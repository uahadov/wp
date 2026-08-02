"""
WordPress plugin indirme ve analiz modülü
"""

import os
import re
import json
import random
import zipfile
import shutil
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import config


class PluginAnalyzer:
    def __init__(self):
        self.work_dir = Path(config.WORK_DIR)
        self.work_dir.mkdir(exist_ok=True)
        self.results_dir = Path(config.RESULTS_DIR)
        self.results_dir.mkdir(exist_ok=True)
        self.scanned_db_path = Path(config.SCANNED_PLUGINS_DB)
        self.scanned_plugins = self._load_scanned_db()

    def _load_scanned_db(self) -> Dict:
        """Daha önce taranan pluginlerin veritabanını güvenli yükle"""
        if self.scanned_db_path.exists():
            try:
                with open(self.scanned_db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    print("⚠️ Veritabanı formatı bozuk, yeni veritabanı oluşturuluyor.")
                    return {}
                return data
            except (json.JSONDecodeError, OSError) as e:
                print(f"⚠️ Veritabanı okuma hatası ({e}), yeni veritabanı oluşturuluyor.")
                return {}
        return {}

    def _save_scanned_db(self):
        """Taranan pluginleri atomic (bozulmaya karşı korumalı) olarak kaydet"""
        try:
            tmp_path = self.scanned_db_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.scanned_plugins, f, indent=2, ensure_ascii=False)
            tmp_path.replace(self.scanned_db_path)
        except Exception as e:
            print(f"⚠️ Veritabanı kaydetme hatası: {e}")

    def mark_as_scanned(self, plugin_slug: str, version: str, found_vulns: bool):
        """Plugin'i tarandı olarak işaretle"""
        self.scanned_plugins[plugin_slug] = {
            "version": version,
            "scanned_at": datetime.now().isoformat(),
            "found_vulnerabilities": found_vulns
        }
        self._save_scanned_db()

    def is_already_scanned(self, plugin_slug: str, version: str) -> bool:
        """Plugin'in bu versiyonu daha önce tarandı mı?"""
        if not getattr(config, "TRACK_SCANNED_PLUGINS", True):
            return False

        if plugin_slug in self.scanned_plugins:
            scanned_version = self.scanned_plugins[plugin_slug].get("version")
            return scanned_version == version
        return False

    def calculate_months_since_update(self, last_updated: str) -> int:
        """Son güncellemeden bu yana geçen ay sayısı"""
        try:
            # "2022-10-15 3:05am GMT" gibi formatları da destekle
            date_str = last_updated.strip().split()[0]
            update_date = datetime.strptime(date_str, "%Y-%m-%d")
            now = datetime.now()
            delta = now - update_date
            return max(0, int(delta.days / 30))
        except Exception:
            return 12  # Varsayılan 1 yıl

    def get_targeted_plugins(self, count: int = 50) -> List[Dict]:
        """Hedefli plugin taraması - az bilinen ve eski pluginler"""
        print(f"🎯 Hedefli plugin taraması başlıyor...")
        all_plugins = []
        filtered_plugins = []

        # Farklı browse kategorileri: sadece "popular" değil çeşitlendiriyoruz
        browse_types = ["popular", "new", "updated"]
        max_page = 100     # 25'ten 100'e çıkarıldı — daha fazla havuz
        sample_size = 8    # 5'ten 8'e çıkarıldı — batch başına daha fazla plugin
        pages_to_scan = random.sample(range(1, max_page + 1), sample_size)

        for page in pages_to_scan:
            browse = random.choice(browse_types)
            print(f"📄 Sayfa {page} ({browse}) taranıyor...")
            try:
                response = requests.get(
                    config.WORDPRESS_API,
                    params={
                        "action": "query_plugins",
                        "request[per_page]": 100,
                        "request[page]": page,
                        "request[browse]": browse
                    },
                    timeout=25,
                    headers={"User-Agent": "WP-Vuln-Scanner/1.0 (Security Research)"}
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                    except Exception:
                        print(f"   ⚠️ JSON parse hatası sayfa {page}")
                        continue

                    plugins = data.get("plugins", [])
                    if plugins:
                        all_plugins.extend(plugins)
                        print(f"   ✓ {len(plugins)} plugin alındı")
                    else:
                        print(f"   ⚠️ Sayfa {page} boş")
                else:
                    print(f"   ❌ HTTP {response.status_code}")

            except requests.exceptions.Timeout:
                print(f"   ❌ Sayfa {page} zaman aşımı")
                continue
            except requests.exceptions.ConnectionError:
                print(f"   ❌ Sayfa {page} bağlantı hatası")
                continue
            except Exception as e:
                print(f"   ❌ Sayfa {page} hatası: {e}")
                continue

        if not all_plugins:
            print("❌ Hiç plugin alınamadı. İnternet veya WordPress API yanıt vermiyor.")
            return []

        print(f"✅ Toplam {len(all_plugins)} plugin çekildi. Filtreleniyor...\n")

        seen_slugs = set()  # Duplicate slug'ları önle
        for plugin in all_plugins:
            try:
                slug = plugin.get("slug", "")
                if not slug or slug in seen_slugs:
                    continue
                seen_slugs.add(slug)

                version = str(plugin.get("version", "1.0.0"))
                active_installs_raw = plugin.get("active_installs", 0)
                # active_installs bazen "1,000+" gibi string gelebilir
                if isinstance(active_installs_raw, str):
                    active_installs = int(re.sub(r"[^0-9]", "", active_installs_raw) or 0)
                else:
                    active_installs = int(active_installs_raw)

                rating = float(plugin.get("rating", 0))
                last_updated = plugin.get("last_updated", "")

                if self.is_already_scanned(slug, version):
                    continue

                if active_installs > config.FILTER_CRITERIA["max_active_installs"]:
                    continue
                if active_installs < config.FILTER_CRITERIA["min_active_installs"]:
                    continue
                if 0 < rating < config.FILTER_CRITERIA["min_rating"]:
                    continue

                months_since_update = (
                    self.calculate_months_since_update(last_updated) if last_updated else 12
                )
                if months_since_update < config.FILTER_CRITERIA["min_months_since_update"]:
                    continue
                if months_since_update > config.FILTER_CRITERIA["max_months_since_update"]:
                    continue

                download_link = plugin.get(
                    "download_link",
                    f"https://downloads.wordpress.org/plugin/{slug}.{version}.zip"
                )

                plugin_info = {
                    "name": plugin.get("name", slug),
                    "slug": slug,
                    "version": version,
                    "download_link": download_link,
                    "author": plugin.get("author", "Unknown"),
                    "rating": rating,
                    "num_ratings": int(plugin.get("num_ratings", 0)),
                    "active_installs": active_installs,
                    "last_updated": last_updated,
                    "months_since_update": months_since_update,
                    "categories": plugin.get("categories", {}),
                    "priority_score": self._calculate_priority_score(plugin, months_since_update)
                }
                filtered_plugins.append(plugin_info)

            except Exception as e:
                # Hatalı plugin verisini sessizce atla (log'a yaz)
                print(f"   ⚠️ Plugin verisi parse hatası: {e}")
                continue

        filtered_plugins.sort(key=lambda x: x["priority_score"], reverse=True)
        result = filtered_plugins[:count]
        print(f"📊 Filtre sonrası {len(result)} plugin taranmaya hazır.")
        return result

    def _calculate_priority_score(self, plugin: Dict, months_since_update: int) -> float:
        """Risk Skoru Hesapla"""
        score = float(months_since_update * 2)
        active_installs = plugin.get("active_installs", 0)
        if isinstance(active_installs, str):
            active_installs = int(re.sub(r"[^0-9]", "", active_installs) or 0)

        if 1000 < active_installs < 10000:
            score += 20
        elif 10000 <= active_installs < 30000:
            score += 10

        categories = str(plugin.get("categories", {})).lower()
        for priority_cat in config.FILTER_CRITERIA["prioritize_categories"]:
            if priority_cat in categories:
                score += 30
                break

        rating = float(plugin.get("rating", 100))
        if 0 < rating < 80:
            score += (80 - rating) / 2

        return score

    def download_plugin(self, plugin: Dict) -> Optional[Path]:
        """Plugin EN SON VERSİYONUNU güvenli indir ve zip'ten çıkar"""
        slug = plugin.get("slug", "")
        if not slug:
            print("❌ Plugin slug eksik, indirme atlandı.")
            return None

        try:
            download_url = plugin.get("download_link", "")

            # API'den güncel versiyon teyidi
            try:
                info_resp = requests.get(
                    config.WORDPRESS_API,
                    params={"action": "plugin_information", "request[slug]": slug},
                    timeout=15,
                    headers={"User-Agent": "WP-Vuln-Scanner/1.0 (Security Research)"}
                )
                if info_resp.status_code == 200:
                    latest_info = info_resp.json()
                    if isinstance(latest_info, dict) and latest_info.get("download_link"):
                        download_url = latest_info["download_link"]
                        plugin["version"] = latest_info.get("version", plugin.get("version", "?"))
            except Exception:
                pass  # API teyidi başarısız, mevcut URL'yi kullan

            if not download_url:
                # Fallback URL'yi dene
                download_url = f"https://downloads.wordpress.org/plugin/{slug}.zip"

            print(f"⬇️  {plugin.get('name', slug)} ({plugin.get('version', '?')}) indiriliyor...")
            response = requests.get(
                download_url,
                timeout=60,
                stream=True,
                headers={"User-Agent": "WP-Vuln-Scanner/1.0 (Security Research)"}
            )
            if response.status_code != 200:
                print(f"❌ İndirme başarısız: HTTP {response.status_code} ({download_url})")
                return None

            # İçerik tipi kontrolü
            content_type = response.headers.get("Content-Type", "")
            if "text/html" in content_type:
                print(f"❌ İndirme başarısız: Sunucu HTML döndürdü (zip bekleniyor)")
                return None

            zip_path = self.work_dir / f"{slug}.zip"
            total_bytes = 0
            max_bytes = 20 * 1024 * 1024  # 20MB limit

            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=16384):
                    f.write(chunk)
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        print(f"❌ Plugin boyutu 20MB'ı aştı, atlanıyor ({slug})")
                        zip_path.unlink(missing_ok=True)
                        return None

            # Geçerli zip dosyası mı kontrol et
            if not zipfile.is_zipfile(zip_path):
                print(f"❌ Geçersiz zip dosyası: {slug}")
                zip_path.unlink(missing_ok=True)
                return None

            extract_path = self.work_dir / slug
            if extract_path.exists():
                shutil.rmtree(extract_path, ignore_errors=True)
            extract_path.mkdir(exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # Zip Slip saldırısına karşı koruma: her dosya yolunu
                # (../, mutlak yol vb.) hedef dizinin dışına taşacak şekilde doğrula.
                # Güvenli olmayan üyeleri ATLAR, yalnızca güvenli olanları ayıklar.
                target_resolved = extract_path.resolve()
                unsafe_members = []
                for member in zip_ref.namelist():
                    if member.endswith("/"):
                        continue
                    member_path = (extract_path / member).resolve()
                    try:
                        is_inside = member_path.is_relative_to(target_resolved)
                    except AttributeError:  # Python < 3.9
                        is_inside = str(member_path).startswith(str(target_resolved))
                    if not is_inside:
                        unsafe_members.append(member)

                if unsafe_members:
                    print(f"⚠️ {len(unsafe_members)} Zip Slip girişimi tespit edildi, atlanıyor: "
                          f"{', '.join(unsafe_members[:5])}")
                    for member in zip_ref.namelist():
                        if member in unsafe_members or member.endswith("/"):
                            continue
                        zip_ref.extract(member, extract_path)
                else:
                    zip_ref.extractall(extract_path)

            zip_path.unlink(missing_ok=True)
            print(f"✅ {plugin.get('name', slug)} indirildi ve açıldı ({total_bytes // 1024}KB)")
            return extract_path

        except Exception as e:
            print(f"❌ Plugin indirme hatası ({slug}): {e}")
            # Temizlik
            try:
                zip_path = self.work_dir / f"{slug}.zip"
                zip_path.unlink(missing_ok=True)
                extract_path = self.work_dir / slug
                if extract_path.exists():
                    shutil.rmtree(extract_path, ignore_errors=True)
            except Exception:
                pass
            return None

    def scan_php_files(self, plugin_path: Path) -> List[Dict]:
        """Plugin içindeki PHP dosyalarını akıllı ve güvenli şekilde tara"""
        php_files = []
        # Üçüncü taraf kütüphaneleri atla (güvenlik hatası değil, bizim kodumuz değil)
        ignore_dirs = [
            "vendor/", "node_modules/", "libs/", "libraries/",
            "third-party/", "assets/", "bower_components/"
        ]
        # Yalnızca boilerplate/stub dosyaları atla (içerikleri bizim kodumuz değil)
        skip_filenames = {"uninstall.php", "index.php", "licence.php", "license.php"}
        max_file_size = 500 * 1024  # 500KB üzeri minified dosyaları atla

        try:
            for php_file in plugin_path.rglob("*.php"):
                if not php_file.is_file():
                    continue

                rel_path = str(php_file.relative_to(plugin_path)).replace("\\", "/")
                file_name_lower = php_file.name.lower()

                if file_name_lower in skip_filenames:
                    continue
                if any(ignored in rel_path.lower() for ignored in ignore_dirs):
                    continue

                try:
                    file_size = php_file.stat().st_size
                except OSError:
                    continue

                if file_size > max_file_size:
                    continue
                if file_size == 0:
                    continue  # Boş dosyaları atla

                try:
                    with open(php_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    # İçerik gerçekten PHP kodu içeriyor mu?
                    if "<?php" not in content and "<?" not in content:
                        continue

                    php_files.append({
                        "path": rel_path,
                        "content": content,
                        "size": file_size
                    })
                except Exception as read_err:
                    print(f"⚠️ Dosya okuma hatası ({php_file.name}): {read_err}")

        except Exception as e:
            print(f"❌ PHP tarama hatası: {e}")

        return php_files

    def quick_pattern_scan(self, php_files: List[Dict]) -> Dict:
        """Regex tabanlı şüpheli kod taraması"""
        findings = {}
        for vuln_type, patterns in config.VULNERABILITY_PATTERNS.items():
            findings[vuln_type] = []
            for php_file in php_files:
                content = php_file.get("content", "")
                if not content:
                    continue
                for pattern in patterns:
                    try:
                        matches = list(re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE))
                        for match in matches:
                            line_num = content[: match.start()].count("\n") + 1
                            findings[vuln_type].append({
                                "file": php_file["path"],
                                "line": line_num,
                                "code": match.group()[:200],  # Çok uzun eşleşmeleri kırp
                                "pattern": pattern
                            })
                    except re.error as re_err:
                        print(f"⚠️ Regex hatası ({vuln_type}): {re_err}")
                        continue
                    except Exception:
                        continue
        return findings

    def cleanup(self, plugin_path: Path, keep: bool = False):
        """Geçici dosyaları güvenli temizle"""
        try:
            if plugin_path and plugin_path.exists():
                if keep:
                    print(f"💾 Saklandı: {plugin_path.name} (zafiyet içeriyor)")
                else:
                    shutil.rmtree(plugin_path, ignore_errors=True)
                    print(f"🧹 Temizlendi: {plugin_path.name}")
        except Exception as e:
            print(f"⚠️ Temizleme uyarısı: {e}")
