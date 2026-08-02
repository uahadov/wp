#!/usr/bin/env python3
"""
WordPress Plugin Vulnerability Scanner v3.0 - Taint Analysis Engine
Ana tarama scripti

v3.0 Değişiklikleri:
- Taint Analysis Engine (TRUE POSITIVE motoru)
- AI artık koddan zafiyet UYDURMUYOR, taint flow'ları DOĞRULUYOR
- Maksimum batch limiti (sonsuz döngü koruması)
- PoC doğrulama desteği (Docker)

Kullanım:
    python3 scanner.py              # Normal tarama
    ./quick-start.sh               # İnteraktif menü
"""

import os
import sys
import json
import time
import re
import logging
import subprocess
import atexit
from pathlib import Path
from datetime import datetime

import config
from plugin_analyzer import PluginAnalyzer
from vuln_detector import VulnerabilityDetector
from telegram_notifier import TelegramNotifier
from taint_analyzer import TaintAnalyzer

# Opsiyonel: bilinen CVE eşleştirme (NVD)
try:
    from cve_matcher import CVEMatcher
    _cve_matcher = CVEMatcher()
except Exception as _e:
    _cve_matcher = None

# Opsiyonel: PoC doğrulama (Docker)
_poc_verifier = None
if getattr(config, "ENABLE_POC_VERIFICATION", False):
    try:
        from poc_verifier import PoCVerifier
        _poc_verifier = PoCVerifier()
    except Exception:
        _poc_verifier = None

# Arka plan bot süreci
bot_process = None


def is_bot_running() -> bool:
    """Telegram botunun arka planda zaten çalışıp çalışmadığını kontrol et"""
    try:
        if sys.platform == "win32":
            output = subprocess.check_output('tasklist /FI "IMAGENAME eq python.exe"', shell=True, text=True)
            cmd = 'wmic process where "name=\'python.exe\'" get commandline'
            res = subprocess.check_output(cmd, shell=True, text=True, errors="replace")
            return "telegram_bot.py" in res
        else:
            res = subprocess.check_output(["pgrep", "-f", "telegram_bot.py"], text=True)
            return bool(res.strip())
    except Exception:
        return False


def start_telegram_bot():
    """Telegram botunu bağımsız (detached) arka plan süreci olarak başlat"""
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("⚠️ Telegram bot token tanımlanmadığı için bot başlatılamadı.")
        return

    if is_bot_running():
        print("🤖 Telegram Bot & AI Asistanı zaten arka planda çalışıyor!")
        return

    try:
        bot_script = Path(__file__).parent / "telegram_bot.py"
        if bot_script.exists():
            if sys.platform == "win32":
                DETACHED_PROCESS = 0x00000008
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                subprocess.Popen(
                    [sys.executable, str(bot_script)],
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                    close_fds=True
                )
            else:
                subprocess.Popen(
                    [sys.executable, str(bot_script)],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            print("🤖 Telegram Bot & AI Asistanı bağımsız arka plan süreci olarak başlatıldı!")
    except Exception as e:
        print(f"⚠️ Telegram botu başlatılırken hata oluştu: {e}")

# Windows console encoding guard
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Temel loglama konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def print_banner():
    """Başlangıç banner'ı"""
    banner = """
+------------------------------------------------------------+
|                                                            |
|        WordPress Plugin Vulnerability Scanner v3.0        |
|             Taint Analysis Engine (TRUE POSITIVE)           |
|                                                            |
+------------------------------------------------------------+
"""
    print(banner)
    print("🔬 Taint Analysis: AKTİF (source -> sink data flow tracking)")
    print("🤖 AI Modu: Taint flow DOĞRULAMA (koddan zafiyet uydurmaz)")
    if config.MAX_BATCHES:
        print(f"🔒 Güvenlik limiti: {config.MAX_BATCHES} batch")
    print()


def validate_config() -> bool:
    """Yapılandırmayı kontrol et"""
    errors = []

    if not config.PRIMARY_API_KEY or config.PRIMARY_API_KEY in ("", "your_github_token_here", "your_gemini_api_key_here"):
        errors.append(
            f"❌ Birincil AI sağlayıcı anahtarı ayarlanmamış "
            f"(GITHUB_TOKEN veya GEMINI_API_KEY) — {config.PRIMARY_PROVIDER} kullanılacak"
        )

    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        errors.append("❌ Telegram bot token ayarlanmamış (TELEGRAM_BOT_TOKEN)")

    if not config.TELEGRAM_CHAT_ID or config.TELEGRAM_CHAT_ID == "your_chat_id_here":
        errors.append("❌ Telegram Chat ID ayarlanmamış (TELEGRAM_CHAT_ID)")

    if errors:
        print("\n".join(errors))
        print("\n⚠️  .env dosyasını düzenleyin ve bilgilerinizi girin\n")
        return False

    return True


def check_known_cves(plugin: dict, plugin_path: Path) -> dict:
    """Bilinen (NVD) CVE'leri eklenti sürümüyle eşleştir."""
    if not getattr(config, "ENABLE_KNOWN_CVE_CHECK", False):
        return {}
    if _cve_matcher is None:
        return {}

    slug = plugin.get("slug", "")
    version = plugin.get("version", "")
    if not slug:
        return {}

    matches = []
    try:
        cves = _cve_matcher.match_plugin_slug(slug)
        for cve in cves:
            ranges = _cve_matcher._collect_ranges(cve)
            if _cve_matcher.version_in_ranges(version, ranges) == "yes":
                matches.append(cve)
    except Exception as e:
        print(f"⚠️ Bilinen CVE kontrolü hatası ({slug}): {e}")
        return {}

    if not matches:
        return {}

    poc_dir = Path(config.RESULTS_DIR) / "poc"
    poc_dir.mkdir(parents=True, exist_ok=True)
    findings = []
    for cve in matches:
        cid = cve.get("id", "?")
        score, sev = _cve_matcher._cvss(cve)
        desc = _cve_matcher._describe(cve)
        refs = _cve_matcher._refs(cve)
        from cve_matcher import generate_poc_template
        fname = re.sub(r"[^A-Za-z0-9_\-]", "_", cid)
        poc_file = poc_dir / f"{fname}.md"
        try:
            poc_file.write_text(
                generate_poc_template(cid, slug, version, desc, refs),
                encoding="utf-8",
            )
        except Exception:
            pass
        findings.append({
            "type": "Known (NVD) CVE",
            "cve_id": cid,
            "severity": sev,
            "cvss_score": score,
            "location": f"/wp-content/plugins/{slug}",
            "description": desc,
            "poc_file": str(poc_file),
        })

    print("\n" + "=" * 60)
    print("🆔 BİLİNEN CVE EŞLEŞMESİ BULUNDU!")
    print("=" * 60)
    for f in findings:
        print(f"  • {f['cve_id']} | CVSS {f['cvss_score']} ({f['severity']}) | {str(f['description'])[:120]}")
    return {"known_vulns": findings}


def save_results(results: dict, plugin_slug: str) -> Path:
    """Sonuçları JSON olarak kaydet"""
    results_dir = Path(config.RESULTS_DIR)
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in plugin_slug)
    filename = results_dir / f"{safe_slug}_{timestamp}.json"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"💾 Sonuçlar kaydedildi: {filename}")
    except Exception as e:
        print(f"⚠️ Sonuç kaydetme hatası: {e}")

    return filename


def print_vuln_details(vulns: list):
    """Bulunan zafiyetleri ekrana detaylı yazdır"""
    print(f"\n🔥 {len(vulns)} GERÇEK VE DOĞRULANMIŞ ZAFİYET BULUNDU!")
    print("=" * 60)
    for i, v in enumerate(vulns, 1):
        print(f"[{i}] Tür: {v.get('type', 'N/A')} | Önem: {v.get('severity', 'N/A')} | CVSS: {v.get('cvss_score', 'N/A')}")
        print(f"    Konum: {v.get('location', v.get('file', 'N/A'))}")
        vuln_code = v.get('vulnerable_code', 'N/A')
        print(f"    Zafiyetli Kod: {str(vuln_code)[:120]}")
        print(f"    PoC / Test Komutu: {v.get('poc_command', 'N/A')}")
        desc = str(v.get('description', 'N/A'))
        print(f"    Açıklama: {desc[:150]}{'...' if len(desc) > 150 else ''}")
        print("-" * 60)


def verify_poc(vulns: list) -> list:
    """PoC'leri Docker üzerinde doğrula (opsiyonel)"""
    if not _poc_verifier:
        return vulns
    verified = []
    for vuln in vulns:
        poc_cmd = vuln.get("poc_command", "")
        if poc_cmd and _poc_verifier.verify_poc(poc_cmd):
            vuln["poc_verified"] = True
            verified.append(vuln)
            print(f"  ✅ PoC DOĞRULANDI: {vuln.get('type', 'Unknown')}")
        else:
            print(f"  ❌ PoC çalışmadı: {vuln.get('type', 'Unknown')}")
    return verified


def check_docker_setup():
    """Docker kurulumunu kontrol et ve kullanıcıya rehberlik et"""
    if not getattr(config, "ENABLE_POC_VERIFICATION", False):
        print("🧪 PoC doğrulama: DEVRE DIŞI (.env: ENABLE_POC_VERIFICATION=false)")
        print("   PoC doğrulama için .env dosyasına ENABLE_POC_VERIFICATION=true ekleyin")
        return

    # Docker kurulu mu?
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("🧪 PoC doğrulama: Docker kurulu değil - DEVRE DIŞI")
            print("   Docker kurmak: https://docs.docker.com/get-docker/")
            return
    except Exception:
        print("🧪 PoC doğrulama: Docker erişilemiyor - DEVRE DIŞI")
        print("   Docker kurmak: https://docs.docker.com/get-docker/")
        return

    # WordPress container çalışıyor mu?
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=wp-test", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=10
        )
        if "wp-test" in result.stdout:
            print("🧪 PoC doğrulama: AKTİF (Docker WordPress çalışıyor)")
        else:
            print("🧪 PoC doğrulama: Docker kurulu ama WordPress container çalışmıyor")
            print("   WordPress container başlatmak için:")
            print("   docker run -d -p 8080:80 --name wp-test wordpress")
            print("   Veya .env dosyasında ENABLE_POC_VERIFICATION=false yapın")
    except Exception:
        print("🧪 PoC doğrulama: Docker kontrol edilemedi - DEVRE DIŞI")


def main():
    """Ana tarama fonksiyonu"""
    print_banner()

    if not validate_config():
        sys.exit(1)

    start_telegram_bot()
    check_docker_setup()

    try:
        analyzer = PluginAnalyzer()
        detector = VulnerabilityDetector()
        notifier = TelegramNotifier()
        taint_analyzer = TaintAnalyzer()
    except Exception as e:
        print(f"❌ Modül başlatma hatası: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("🚀 Tarama başlatılıyor...")
    print("🎯 Mod: ZAFİYET BULANA KADAR DEVAM ET (TAINT ANALYSIS)")
    print(f"🔒 Maksimum batch: {config.MAX_BATCHES}")
    print()

    total_scanned = 0
    total_vulns_found = 0
    skipped_count = 0
    batch_number = 1
    max_batches = getattr(config, "MAX_BATCHES", 20)

    while total_vulns_found == 0 and batch_number <= max_batches:
        print(f"\n{'='*60}")
        print(f"🔄 BATCH #{batch_number}/{max_batches} - Yeni pluginler getiriliyor...")
        print(f"{'='*60}\n")

        plugins = analyzer.get_targeted_plugins(count=config.PLUGINS_PER_SCAN * 3)

        if not plugins:
            print("⚠️  Yeni plugin bulunamadı, 30 saniye bekleniyor...")
            time.sleep(30)
            batch_number += 1
            continue

        batch_scanned = 0

        if batch_number == 1:
            notifier.send_scan_start(len(plugins))

        for idx, plugin in enumerate(plugins, 1):

            if batch_scanned >= config.PLUGINS_PER_SCAN:
                print(f"\n✅ Bu batch'te {config.PLUGINS_PER_SCAN} plugin tarandı, durduruluyor...")
                break

            print(f"\n{'='*60}")
            print(f"[{idx}/{len(plugins)}] 📦 {plugin.get('name', 'Unknown')} v{plugin.get('version', '?')}")
            print(f"⭐ Rating: {plugin.get('rating', 0)}/100 ({plugin.get('num_ratings', 0)} derecelendirme)")
            print(f"📊 Active Installs: {plugin.get('active_installs', 0):,}")
            print(f"⏰ Son güncelleme: {plugin.get('months_since_update', 0)} ay önce")
            print(f"🎯 Öncelik skoru: {plugin.get('priority_score', 0):.1f}")
            print(f"{'='*60}\n")

            plugin_path = analyzer.download_plugin(plugin)
            if not plugin_path:
                print("⚠️  Plugin indirilemedi, atlanıyor\n")
                skipped_count += 1
                continue

            known_cves = check_known_cves(plugin, plugin_path)
            if known_cves.get("known_vulns"):
                report_with_known = {
                    "plugin": plugin,
                    "vulnerabilities_found": known_cves["known_vulns"],
                }
                save_results(report_with_known, plugin["slug"])
                notifier.send_vulnerability_report(report_with_known)
                total_vulns_found += 1
                analyzer.cleanup(plugin_path, keep=True)
                print("\n" + "=" * 60)
                print(f"✅ BİLİNEN CVE EŞLEŞMESİ İLE HEDEF TAMAMLANDI! ({plugin['slug']})")
                print("=" * 60)
                break

            php_files = analyzer.scan_php_files(plugin_path)
            print(f"📄 {len(php_files)} PHP dosyası bulundu")

            if not php_files:
                analyzer.cleanup(plugin_path, keep=False)
                skipped_count += 1
                analyzer.mark_as_scanned(plugin["slug"], plugin["version"], False)
                total_scanned += 1
                batch_scanned += 1
                continue

            # ================================================================
            # TAINT ANALYSIS (TRUE POSITIVE MOTORU)
            # ================================================================
            print("🔬 Taint Analysis başlıyor...")
            taint_flows = taint_analyzer.analyze_files(php_files)

            if not taint_flows:
                print("✅ Taint akışı bulunamadı (temiz plugin)")
                analyzer.mark_as_scanned(plugin["slug"], plugin["version"], False)
                analyzer.cleanup(plugin_path, keep=False)
                total_scanned += 1
                batch_scanned += 1
                continue

            # Taint akışı olan dosyaları belirle
            flows_by_file = {}
            for flow in taint_flows:
                fname = flow.get("file", "")
                if fname not in flows_by_file:
                    flows_by_file[fname] = []
                flows_by_file[fname].append(flow)

            suspicious_files = []
            for php_file in php_files:
                if php_file["path"] in flows_by_file:
                    suspicious_files.append(php_file)

            print(f"🔍 {len(suspicious_files)} dosyada {len(taint_flows)} taint akışı tespit edildi")

            found_vulns_this_plugin = False

            if suspicious_files:
                # AI ile taint flow doğrulama
                results = detector.deep_analyze(plugin, suspicious_files, taint_flows)
                results = detector.filter_high_confidence_vulns(results)

                # PoC doğrulama (opsiyonel - Docker)
                if _poc_verifier and results.get("vulnerabilities_found"):
                    results["vulnerabilities_found"] = verify_poc(results["vulnerabilities_found"])

                save_results(results, plugin["slug"])

                vulns = results.get("vulnerabilities_found", [])
                found_vulns_this_plugin = len(vulns) > 0

                analyzer.mark_as_scanned(plugin["slug"], plugin["version"], found_vulns_this_plugin)

                if found_vulns_this_plugin:
                    print_vuln_details(vulns)
                    print("📱 Detaylı Telegram bildirimi gönderiliyor...")
                    notifier.send_vulnerability_report(results)
                    total_vulns_found += 1
                    print("\n" + "="*60)
                    print("✅ HEDEF TAMAMLANDI! GERÇEK ZAFİYET BULUNDU!")
                    print("="*60)
                    analyzer.cleanup(plugin_path, keep=True)
                else:
                    print("\n✅ Doğrulanabilir zafiyet bulunamadı")
                    analyzer.cleanup(plugin_path, keep=False)
            else:
                print("✅ Taint akışı yok (temiz)")
                analyzer.mark_as_scanned(plugin["slug"], plugin["version"], False)
                analyzer.cleanup(plugin_path, keep=False)

            total_scanned += 1
            batch_scanned += 1

            if total_vulns_found > 0:
                break

            if idx < len(plugins) and batch_scanned < config.PLUGINS_PER_SCAN:
                print("\n⏱️  Sonraki plugin için 5 saniye bekleniyor...")
                time.sleep(5)

        if total_vulns_found > 0:
            print("\n🎊 ARAMA DURDURULDU - ZAFİYET BULUNDU!")
            break

        print(f"\n⚠️  Batch #{batch_number} tamamlandı - Zafiyet bulunamadı")
        batch_number += 1
        if batch_number <= max_batches:
            print("🔄 Yeni batch başlatılıyor...\n")
            time.sleep(10)

    if batch_number > max_batches and total_vulns_found == 0:
        print(f"\n⚠️  Maksimum batch limitine ({max_batches}) ulaşıldı.")
        print("   Daha fazla tarama için tekrar çalıştırın veya MAX_BATCHES'i artırın.")

    print(f"\n{'='*60}")
    print("✅ TARAMA TAMAMLANDI")
    print(f"{'='*60}")
    print(f"📊 Toplam taranan plugin: {total_scanned}")
    print(f"⏭️  Atlanan plugin: {skipped_count}")
    print(f"🚨 Zafiyet bulunan plugin: {total_vulns_found}")
    print(f"💾 Taranan pluginler veritabanına kaydedildi")
    print(f"{'='*60}\n")

    notifier.send_scan_complete(total_scanned, total_vulns_found)

    if total_vulns_found > 0:
        print("🎉 Tebrikler! Potansiyel CVE adayı buldunuz!")
        print("📌 Sonraki adımlar:")
        print("   1. results/ klasöründeki raporları inceleyin")
        print("   2. Zafiyeti manuel olarak doğrulayın")
        print("   3. Plugin geliştiricisine özel olarak bildirin")
        print("   4. 90 gün sonra CVE başvurusu yapın: https://cveform.mitre.org/")
        print("\n⚠️  Lütfen etik ve yasal kurallara uyun!\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tarama kullanıcı tarafından durduruldu")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Kritik hata: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)