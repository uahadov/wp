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
from pathlib import Path
from datetime import datetime

import config
from plugin_analyzer import PluginAnalyzer
from vuln_detector import VulnerabilityDetector
from telegram_notifier import TelegramNotifier


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


def validate_config():
    """Yapılandırmayı kontrol et"""
    errors = []
    
    if config.GITHUB_TOKEN == "your_github_token_here":
        errors.append("❌ GitHub AI Models API token ayarlanmamış")
    
    if config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        errors.append("❌ Telegram bot token ayarlanmamış")
    
    if errors:
        print("\n".join(errors))
        print("\n⚠️  config.py dosyasını düzenleyin ve bilgilerinizi girin\n")
        return False
    
    return True


def save_results(results: dict, plugin_slug: str):
    """Sonuçları JSON olarak kaydet"""
    results_dir = Path(config.RESULTS_DIR)
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = results_dir / f"{plugin_slug}_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Sonuçlar kaydedildi: {filename}")
    return filename


def main():
    """Ana tarama fonksiyonu"""
    print_banner()
    
    # Yapılandırmayı kontrol et
    if not validate_config():
        sys.exit(1)
    
    # Modülleri başlat
    analyzer = PluginAnalyzer()
    detector = VulnerabilityDetector()
    notifier = TelegramNotifier()
    
    print("🚀 Tarama başlatılıyor...")
    print("🎯 Mod: ZAFIYET BULANA KADAR DEVAM ET")
    print()
    
    # İstatistikler
    total_scanned = 0
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
        
        # İlk batch'te bildirim gönder
        if batch_number == 1:
            notifier.send_scan_start(len(plugins))
        
        # Her plugin için tarama yap
        for idx, plugin in enumerate(plugins, 1):
            
            # Belirli sayıda plugin tarandıysa dur
            if total_scanned >= config.PLUGINS_PER_SCAN:
                print(f"\n✅ Hedef {config.PLUGINS_PER_SCAN} plugin tarandı, durduruluyor...")
                break
            
            print(f"\n{'='*60}")
            print(f"[{idx}/{len(plugins)}] 📦 {plugin['name']} v{plugin['version']}")
            print(f"⭐ Rating: {plugin['rating']}/100 ({plugin['num_ratings']} derecelendirme)")
            print(f"📊 Active Installs: {plugin['active_installs']:,}")
            print(f"⏰ Son güncelleme: {plugin['months_since_update']} ay önce")
            print(f"🎯 Öncelik skoru: {plugin['priority_score']:.1f}")
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
                # Yine de tarandı olarak işaretle
                analyzer.mark_as_scanned(plugin["slug"], plugin["version"], False)
                continue
            
            # Hızlı pattern taraması
            pattern_findings = analyzer.quick_pattern_scan(php_files)
            
            # Şüpheli dosyaları belirle
            suspicious_files = []
            for php_file in php_files:
                # Pattern bulgusu olan dosyaları şüpheli olarak işaretle
                is_suspicious = False
                for vuln_type, findings in pattern_findings.items():
                    if any(f["file"] == php_file["path"] for f in findings):
                        is_suspicious = True
                        break
                
                if is_suspicious:
                    suspicious_files.append(php_file)
            
            print(f"🔍 {len(suspicious_files)} şüpheli dosya tespit edildi")
            
            if suspicious_files:
                # AI ile derin analiz
                results = detector.deep_analyze(plugin, suspicious_files)
                
                # Yüksek güvenirlikli zafiyetleri filtrele
                results = detector.filter_high_confidence_vulns(results)
                
                # Sonuçları kaydet
                save_results(results, plugin["slug"])
                
                # Zafiyet var mı kontrol et
                found_vulns = len(results["vulnerabilities_found"]) > 0
                
                # Tarandı olarak işaretle
                analyzer.mark_as_scanned(plugin["slug"], plugin["version"], found_vulns)
                
                # Zafiyet bulunduysa Telegram'a bildir ve detayları ekrana yaz
                if found_vulns:
                    print(f"\n🔥 {len(results['vulnerabilities_found'])} GERÇEK VE DOĞRULANMIŞ ZAFIYET BULUNDU!")
                    print("=" * 60)
                    for idx, v in enumerate(results["vulnerabilities_found"], 1):
                        print(f"[{idx}] Tür: {v.get('type')} | Önem: {v.get('severity')} | CVSS: {v.get('cvss_score')}")
                        print(f"    Konum: {v.get('location', v.get('file'))}")
                        print(f"    Zafiyetli Kod: {v.get('vulnerable_code', 'N/A')}")
                        print(f"    PoC / Test Komutu: {v.get('poc_command', 'N/A')}")
                        print(f"    Açıklama: {v.get('description', 'N/A')[:150]}...")
                        print("-" * 60)
                    
                    print("📱 Detaylı Telegram bildirimi gönderiliyor...")
                    notifier.send_vulnerability_report(results)
                    total_vulns_found += 1
                    
                    # ZAFİYET BULUNDU - ARAMAYA DEVAM ETME!
                    print("\n" + "="*60)
                    print("✅ HEDEF TAMAMLANDI! GERÇEK ZAFIYET BULUNDU!")
                    print("="*60)
                    
                    # Zafiyet bulunan plugin'i SAKLAYALIM (cleanup'a keep=True)
                    analyzer.cleanup(plugin_path, keep=True)
                    
                else:
                    print("\n✅ Doğrulanabilir zafiyet bulunamadı")
                    
                    # ZAFİYET YOK - PLUGIN DOSYALARINI SİL
                    analyzer.cleanup(plugin_path, keep=False)
            else:
                print("✅ Şüpheli kod bulunamadı")
                # Tarandı olarak işaretle (zafiyet yok)
                analyzer.mark_as_scanned(plugin["slug"], plugin["version"], False)
                # Temizle (zafiyet yok)
                analyzer.cleanup(plugin_path, keep=False)
            
            total_scanned += 1
            
            # ZAFİYET BULUNDUYSA DÖNGÜDEN ÇIK
            if total_vulns_found > 0:
                break
            
            # Rate limiting için bekleme
            if idx < len(plugins):
                print("\n⏱️  Sonraki plugin için 5 saniye bekleniyor...")
                time.sleep(5)
        
        # ZAFİYET BULUNDUYSA DÖNGÜYÜ KIR
        if total_vulns_found > 0:
            print("\n🎊 ARAMA DURDURULDU - ZAFİYET BULUNDU!")
            break
        
        # Batch tamamlandı, zafiyet bulunamadı
        if total_vulns_found == 0:
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
