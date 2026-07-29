#!/usr/bin/env python3
"""
WordPress Plugin Vulnerability Scanner
Ana tarama scripti

Kullanım:
    python3 scanner.py              # Normal tarama
    ./quick-start.sh               # İnteraktif menü
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

import config
from plugin_analyzer import PluginAnalyzer
from vuln_detector import VulnerabilityDetector
from telegram_notifier import TelegramNotifier

# Temel loglama konfigürasyonu
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


def print_banner():
    """Başlangıç banner'ı"""
    banner = """
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        WordPress Plugin Vulnerability Scanner             ║
║                   AI Powered Security                      ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
"""
    print(banner)


def validate_config() -> bool:
    """Yapılandırmayı kontrol et"""
    errors = []

    if not config.GITHUB_TOKEN or config.GITHUB_TOKEN == "your_github_token_here":
        errors.append("❌ GitHub AI Models API token ayarlanmamış (GITHUB_TOKEN)")

    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        errors.append("❌ Telegram bot token ayarlanmamış (TELEGRAM_BOT_TOKEN)")

    if not config.TELEGRAM_CHAT_ID or config.TELEGRAM_CHAT_ID == "your_chat_id_here":
        errors.append("❌ Telegram Chat ID ayarlanmamış (TELEGRAM_CHAT_ID)")

    if errors:
        print("\n".join(errors))
        print("\n⚠️  .env dosyasını düzenleyin ve bilgilerinizi girin\n")
        return False

    return True


def save_results(results: dict, plugin_slug: str) -> Path:
    """Sonuçları JSON olarak kaydet"""
    results_dir = Path(config.RESULTS_DIR)
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Slug'da özel karakterleri temizle (dosya adı güvenliği)
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


def main():
    """Ana tarama fonksiyonu"""
    print_banner()

    # Yapılandırmayı kontrol et
    if not validate_config():
        sys.exit(1)

    # Modülleri başlat
    try:
        analyzer = PluginAnalyzer()
        detector = VulnerabilityDetector()
        notifier = TelegramNotifier()
    except Exception as e:
        print(f"❌ Modül başlatma hatası: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("🚀 Tarama başlatılıyor...")
    print("🎯 Mod: ZAFİYET BULANA KADAR DEVAM ET")
    print()

    # İstatistikler
    total_scanned = 0      # Tüm batch'lerde toplam taranan
    total_vulns_found = 0
    skipped_count = 0
    batch_number = 1

    # ZAFİYET BULANA KADAR DÖNGÜ
    while total_vulns_found == 0:
        print(f"\n{'='*60}")
        print(f"🔄 BATCH #{batch_number} - Yeni pluginler getiriliyor...")
        print(f"{'='*60}\n")

        # HEDEFLENMIŞ plugin taraması (az bilinen, eski pluginler)
        plugins = analyzer.get_targeted_plugins(count=config.PLUGINS_PER_SCAN * 3)

        if not plugins:
            print("⚠️  Yeni plugin bulunamadı, 30 saniye bekleniyor...")
            time.sleep(30)
            continue

        # Bu batch'teki tarama sayacı — her batch başında sıfır
        batch_scanned = 0

        # İlk batch'te bildirim gönder
        if batch_number == 1:
            notifier.send_scan_start(len(plugins))

        # Her plugin için tarama yap
        for idx, plugin in enumerate(plugins, 1):

            # Bu batch'te belirli sayıda plugin tarandıysa dur
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

            # Plugin'i indir
            plugin_path = analyzer.download_plugin(plugin)
            if not plugin_path:
                print("⚠️  Plugin indirilemedi, atlanıyor\n")
                skipped_count += 1
                continue

            # PHP dosyalarını tara
            php_files = analyzer.scan_php_files(plugin_path)
            print(f"📄 {len(php_files)} PHP dosyası bulundu")

            if not php_files:
                analyzer.cleanup(plugin_path, keep=False)
                skipped_count += 1
                # Tarandı olarak işaretle (PHP dosyası yok = zafiyet yok)
                analyzer.mark_as_scanned(plugin["slug"], plugin["version"], False)
                total_scanned += 1
                batch_scanned += 1
                continue

            # Hızlı pattern taraması
            pattern_findings = analyzer.quick_pattern_scan(php_files)

            # Şüpheli dosyaları belirle
            suspicious_files = []
            suspicious_file_paths = set()
            for vuln_type, findings in pattern_findings.items():
                for finding in findings:
                    fpath = finding.get("file", "")
                    if fpath and fpath not in suspicious_file_paths:
                        suspicious_file_paths.add(fpath)

            for php_file in php_files:
                if php_file["path"] in suspicious_file_paths:
                    suspicious_files.append(php_file)

            print(f"🔍 {len(suspicious_files)} şüpheli dosya tespit edildi")

            found_vulns_this_plugin = False

            if suspicious_files:
                # AI ile derin analiz
                results = detector.deep_analyze(plugin, suspicious_files)

                # Yüksek güvenirlikli zafiyetleri filtrele
                results = detector.filter_high_confidence_vulns(results)

                # Sonuçları kaydet
                save_results(results, plugin["slug"])

                # Zafiyet var mı kontrol et
                vulns = results.get("vulnerabilities_found", [])
                found_vulns_this_plugin = len(vulns) > 0

                # Tarandı olarak işaretle
                analyzer.mark_as_scanned(plugin["slug"], plugin["version"], found_vulns_this_plugin)

                if found_vulns_this_plugin:
                    print_vuln_details(vulns)

                    print("📱 Detaylı Telegram bildirimi gönderiliyor...")
                    notifier.send_vulnerability_report(results)
                    total_vulns_found += 1

                    # ZAFİYET BULUNDU - ARAMAYA DEVAM ETME!
                    print("\n" + "="*60)
                    print("✅ HEDEF TAMAMLANDI! GERÇEK ZAFIYET BULUNDU!")
                    print("="*60)

                    # Zafiyet bulunan plugin'i SAKLAYALIM
                    analyzer.cleanup(plugin_path, keep=True)
                else:
                    print("\n✅ Doğrulanabilir zafiyet bulunamadı")
                    analyzer.cleanup(plugin_path, keep=False)
            else:
                print("✅ Şüpheli kod bulunamadı")
                # Tarandı olarak işaretle (zafiyet yok)
                analyzer.mark_as_scanned(plugin["slug"], plugin["version"], False)
                # Temizle
                analyzer.cleanup(plugin_path, keep=False)

            total_scanned += 1
            batch_scanned += 1

            # ZAFİYET BULUNDUYSA DÖNGÜDEN ÇIK
            if total_vulns_found > 0:
                break

            # Rate limiting için bekleme (son plugin değilse)
            if idx < len(plugins) and batch_scanned < config.PLUGINS_PER_SCAN:
                print("\n⏱️  Sonraki plugin için 5 saniye bekleniyor...")
                time.sleep(5)

        # ZAFİYET BULUNDUYSA DÖNGÜYÜ KIR
        if total_vulns_found > 0:
            print("\n🎊 ARAMA DURDURULDU - ZAFİYET BULUNDU!")
            break

        # Batch tamamlandı, zafiyet bulunamadı
        print(f"\n⚠️  Batch #{batch_number} tamamlandı - Zafiyet bulunamadı")
        print("🔄 Yeni batch başlatılıyor...\n")
        batch_number += 1
        time.sleep(10)  # Kısa bekleme

    # Tarama tamamlandı bildirimi
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
