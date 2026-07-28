"""
WordPress plugin indirme ve analiz modülü
"""

import os
import re
import json
import zipfile
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import config


class PluginAnalyzer:
    def __init__(self):
        self.work_dir = Path(config.WORK_DIR)
        self.work_dir.mkdir(exist_ok=True)
        self.scanned_db_path = Path(config.SCANNED_PLUGINS_DB)
        self.scanned_plugins = self._load_scanned_db()
    
    def _load_scanned_db(self) -> Dict:
        """Daha önce taranan pluginlerin veritabanını yükle"""
        if self.scanned_db_path.exists():
            try:
                with open(self.scanned_db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_scanned_db(self):
        """Taranan pluginleri kaydet"""
        with open(self.scanned_db_path, "w", encoding="utf-8") as f:
            json.dump(self.scanned_plugins, f, indent=2, ensure_ascii=False)
    
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
        if not config.TRACK_SCANNED_PLUGINS:
            return False
        
        if plugin_slug in self.scanned_plugins:
            scanned_version = self.scanned_plugins[plugin_slug].get("version")
            return scanned_version == version
        return False
    
    def calculate_months_since_update(self, last_updated: str) -> int:
        """Son güncellemeden bu yana geçen ay sayısı"""
        try:
            # WordPress API formatı: "2023-05-15 3:42pm GMT"
            update_date = datetime.strptime(last_updated.split()[0], "%Y-%m-%d")
            now = datetime.now()
            delta = now - update_date
            return int(delta.days / 30)
        except:
            return 0
    
    def get_targeted_plugins(self, count: int = 50) -> List[Dict]:
        """Hedefli plugin taraması - az bilinen ve eski pluginler"""
        print(f"🎯 Hedefli plugin taraması başlıyor...")
        print(f"📊 Kriterler:")
        print(f"   • Aktif kurulum: {config.FILTER_CRITERIA['min_active_installs']:,} - {config.FILTER_CRITERIA['max_active_installs']:,}")
        print(f"   • Son güncelleme: {config.FILTER_CRITERIA['min_months_since_update']}-{config.FILTER_CRITERIA['max_months_since_update']} ay önce")
        print(f"   • Minimum rating: {config.FILTER_CRITERIA['min_rating']}/100")
        print()
        
        all_plugins = []
        filtered_plugins = []
        
        try:
            # Birden fazla sayfadan plugin çek
            for page in range(1, 6):  # 5 sayfa tara (her sayfa 100 plugin)
                print(f"📄 Sayfa {page} taranıyor...")
                
                response = requests.get(
                    f"{config.WORDPRESS_API}",
                    params={
                        "action": "query_plugins",
                        "request[per_page]": 100,
                        "request[page]": page,
                        "request[browse]": "updated"  # Son güncellenen (eski olanları bul)
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    all_plugins.extend(data.get("plugins", []))
            
            print(f"✅ Toplam {len(all_plugins)} plugin bulundu")
            print(f"🔍 Filtreleme yapılıyor...\n")
            
            # Filtreleme yap
            for plugin in all_plugins:
                slug = plugin.get("slug")
                version = plugin.get("version")
                active_installs = plugin.get("active_installs", 0)
                rating = plugin.get("rating", 0)
                last_updated = plugin.get("last_updated", "")
                
                # Daha önce tarandı mı kontrol et
                if self.is_already_scanned(slug, version):
                    continue
                
                # Aktif kurulum filtresi
                if active_installs > config.FILTER_CRITERIA["max_active_installs"]:
                    continue
                if active_installs < config.FILTER_CRITERIA["min_active_installs"]:
                    continue
                
                # Rating filtresi
                if rating < config.FILTER_CRITERIA["min_rating"]:
                    continue
                
                # Güncelleme tarihi filtresi
                months_since_update = self.calculate_months_since_update(last_updated)
                if months_since_update < config.FILTER_CRITERIA["min_months_since_update"]:
                    continue
                if months_since_update > config.FILTER_CRITERIA["max_months_since_update"]:
                    continue
                
                # Filtreyi geçti!
                plugin_info = {
                    "name": plugin.get("name"),
                    "slug": slug,
                    "version": version,
                    "download_link": plugin.get("download_link"),
                    "author": plugin.get("author"),
                    "rating": rating,
                    "num_ratings": plugin.get("num_ratings"),
                    "active_installs": active_installs,
                    "last_updated": last_updated,
                    "months_since_update": months_since_update,
                    "categories": plugin.get("categories", {}),
                    "priority_score": self._calculate_priority_score(plugin, months_since_update)
                }
                
                filtered_plugins.append(plugin_info)
            
            # Öncelik skoruna göre sırala (en yüksek risk en üstte)
            filtered_plugins.sort(key=lambda x: x["priority_score"], reverse=True)
            
            # İstenen sayıda plugin döndür
            result = filtered_plugins[:count]
            
            print(f"✅ {len(result)} hedef plugin belirlendi")
            print(f"📊 Ortalama son güncelleme: {sum(p['months_since_update'] for p in result) / len(result):.1f} ay önce")
            print()
            
            return result
            
        except Exception as e:
            print(f"❌ Plugin listesi alınamadı: {e}")
            return []
    
    def _calculate_priority_score(self, plugin: Dict, months_since_update: int) -> float:
        """Plugin'in zafiyet bulunma olasılığını skorla"""
        score = 0.0
        
        # Eski plugin = daha yüksek risk
        score += months_since_update * 2
        
        # Orta popülerlik = daha az incelenmiş
        active_installs = plugin.get("active_installs", 0)
        if 1000 < active_installs < 10000:
            score += 20
        elif 10000 < active_installs < 30000:
            score += 10
        
        # Öncelikli kategoriler
        categories = plugin.get("categories", {})
        for priority_cat in config.FILTER_CRITERIA["prioritize_categories"]:
            if priority_cat in str(categories).lower():
                score += 30
        
        # Düşük rating = olası kod kalitesi sorunları
        rating = plugin.get("rating", 100)
        if rating < 80:
            score += (80 - rating) / 2
        
        return score
    
    def download_plugin(self, plugin: Dict) -> Optional[Path]:
        """Plugin'in EN SON VERSİYONUNU indir"""
        try:
            slug = plugin["slug"]
            
            # EN SON VERSİYONU API'den al (güncel olduğundan emin ol)
            print(f"🔄 {plugin['name']} için en son versiyon kontrol ediliyor...")
            
            try:
                info_response = requests.get(
                    f"{config.WORDPRESS_API}",
                    params={
                        "action": "plugin_information",
                        "request[slug]": slug
                    },
                    timeout=30
                )
                
                if info_response.status_code == 200:
                    latest_info = info_response.json()
                    latest_version = latest_info.get("version")
                    download_url = latest_info.get("download_link")
                    
                    print(f"✅ En son versiyon: {latest_version}")
                    
                    # Versiyon güncellemesi var mı kontrol et
                    if latest_version != plugin["version"]:
                        print(f"⚠️  Versiyon farkı: {plugin['version']} → {latest_version}")
                        plugin["version"] = latest_version  # Güncelle
                else:
                    # API başarısız olursa mevcut download link'i kullan
                    download_url = plugin["download_link"]
                    print(f"⚠️  API'den versiyon alınamadı, mevcut link kullanılıyor")
            except:
                download_url = plugin["download_link"]
                print(f"⚠️  Versiyon kontrolü başarısız, mevcut link kullanılıyor")
            
            print(f"⬇️  {plugin['name']} ({plugin['version']}) indiriliyor...")
            
            # Plugin'i indir
            response = requests.get(download_url, timeout=60, stream=True)
            if response.status_code != 200:
                print(f"❌ İndirme başarısız: HTTP {response.status_code}")
                return None
            
            # ZIP dosyasını kaydet
            zip_path = self.work_dir / f"{slug}.zip"
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # ZIP'i aç
            extract_path = self.work_dir / slug
            extract_path.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_path)
            
            # ZIP dosyasını sil (disk tasarrufu)
            zip_path.unlink()
            
            print(f"✅ {plugin['name']} indirildi ve açıldı")
            return extract_path
            
        except Exception as e:
            print(f"❌ Plugin indirme hatası: {e}")
            return None
    
    def scan_php_files(self, plugin_path: Path) -> List[Dict]:
        """Plugin içindeki PHP dosyalarını tara"""
        php_files = []
        
        try:
            for php_file in plugin_path.rglob("*.php"):
                if php_file.is_file():
                    # Dosya boyutunu kontrol et (çok büyük dosyaları atla)
                    if php_file.stat().st_size > 500 * 1024:  # 500KB üzeri
                        continue
                    
                    try:
                        with open(php_file, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            
                        php_files.append({
                            "path": str(php_file.relative_to(plugin_path)),
                            "content": content,
                            "size": php_file.stat().st_size
                        })
                    except Exception as e:
                        print(f"⚠️  Dosya okunamadı: {php_file.name} - {e}")
                        
        except Exception as e:
            print(f"❌ PHP dosyaları tarama hatası: {e}")
        
        return php_files
    
    def quick_pattern_scan(self, php_files: List[Dict]) -> Dict:
        """Hızlı regex tabanlı zafiyet taraması"""
        findings = {}
        
        for vuln_type, patterns in config.VULNERABILITY_PATTERNS.items():
            findings[vuln_type] = []
            
            for php_file in php_files:
                content = php_file["content"]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        # Satır numarasını bul
                        line_num = content[:match.start()].count("\n") + 1
                        
                        # Eğer CSRF kontrolü yapılıyorsa, bu iyi bir şey (zafiyet değil)
                        if vuln_type == "CSRF" and ("wp_nonce" in match.group() or "check_admin_referer" in match.group()):
                            continue
                        
                        findings[vuln_type].append({
                            "file": php_file["path"],
                            "line": line_num,
                            "code": match.group(),
                            "pattern": pattern
                        })
        
        return findings
    
    def cleanup(self, plugin_path: Path, keep=False):
        """Geçici dosyaları temizle
        
        Args:
            plugin_path: Plugin dizini
            keep: True ise silme (zafiyet bulundu)
        """
        try:
            import shutil
            if plugin_path.exists():
                if keep:
                    print(f"💾 Saklandı: {plugin_path.name} (zafiyet var - silinmedi)")
                else:
                    shutil.rmtree(plugin_path)
                    print(f"🧹 Temizlendi: {plugin_path.name}")
        except Exception as e:
            print(f"⚠️  Temizleme hatası: {e}")
