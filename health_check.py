#!/usr/bin/env python3
"""
Health Check & System Status
=============================

Sistemin sağlık durumunu kontrol et
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

import config
from database import get_db
from logger import get_logger


class HealthChecker:
    """Sistem sağlık kontrolü"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.ok_items = []
    
    def check_database(self):
        """Database durumu"""
        try:
            db = get_db()
            size = db.get_database_size()
            
            if size > 100:  # 100MB
                self.warnings.append(f"⚠️ Database çok büyük: {size:.1f}MB (VACUUM önerilir)")
            elif size > 50:
                self.warnings.append(f"⚠️ Database boyutu yüksek: {size:.1f}MB")
            else:
                self.ok_items.append(f"✅ Database: OK ({size:.1f}MB)")
            
            # Test query
            stats = db.get_stats()
            self.ok_items.append(f"   • {stats['total_plugins_scanned']} plugin, {stats['total_vulnerabilities_found']} zafiyet")
            
        except Exception as e:
            self.issues.append(f"❌ Database: HATA - {e}")
    
    def check_logs(self):
        """Log dosyaları durumu"""
        try:
            log_dir = Path("./logs")
            if not log_dir.exists():
                self.issues.append("❌ Logs dizini yok")
                return
            
            total_size = sum(f.stat().st_size for f in log_dir.rglob("*") if f.is_file()) / (1024 * 1024)
            
            if total_size > 100:
                self.warnings.append(f"⚠️ Log dosyaları çok büyük: {total_size:.1f}MB (temizlik önerilir)")
            else:
                self.ok_items.append(f"✅ Logs: OK ({total_size:.1f}MB/40MB)")
            
        except Exception as e:
            self.issues.append(f"❌ Logs: HATA - {e}")
    
    def check_disk_space(self):
        """Disk alanı"""
        try:
            total, used, free = shutil.disk_usage(".")
            free_percent = (free / total) * 100
            used_percent = (used / total) * 100
            
            if free_percent < 10:
                self.issues.append(f"❌ Disk dolu: %{used_percent:.0f} kullanımda (sadece %{free_percent:.0f} boş)")
            elif free_percent < 20:
                self.warnings.append(f"⚠️ Disk dolmak üzere: %{used_percent:.0f} kullanımda")
            else:
                self.ok_items.append(f"✅ Disk: OK (%{free_percent:.0f} boş)")
            
        except Exception as e:
            self.issues.append(f"❌ Disk: HATA - {e}")
    
    def check_api_keys(self):
        """API anahtarları"""
        try:
            # Primary API
            if not config.PRIMARY_API_KEY or config.PRIMARY_API_KEY in ("", "your_github_token_here", "your_gemini_api_key_here"):
                self.issues.append(f"❌ {config.PRIMARY_PROVIDER} API key eksik")
            else:
                self.ok_items.append(f"✅ {config.PRIMARY_PROVIDER} API: OK")
            
            # Secondary API
            if config.SECONDARY_API_KEY and config.SECONDARY_API_KEY not in ("", "your_github_token_here", "your_gemini_api_key_here"):
                self.ok_items.append(f"✅ {config.SECONDARY_PROVIDER} API: OK")
            
            # Telegram
            if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
                self.issues.append("❌ Telegram bot token eksik")
            else:
                self.ok_items.append("✅ Telegram bot token: OK")
            
        except Exception as e:
            self.issues.append(f"❌ API keys: HATA - {e}")
    
    def check_api_usage(self):
        """API kullanım istatistikleri"""
        try:
            db = get_db()
            
            # GitHub usage
            github_count = db.get_api_usage_last_hour(config.PRIMARY_PROVIDER)
            github_limit_count = db.get_rate_limit_count_today(config.PRIMARY_PROVIDER)
            
            if github_limit_count > 10:
                self.warnings.append(f"⚠️ {config.PRIMARY_PROVIDER} bugün {github_limit_count}x rate limit yedi")
            else:
                self.ok_items.append(f"✅ {config.PRIMARY_PROVIDER} API: {github_count} calls/hour")
            
            # Secondary API
            if config.SECONDARY_API_KEY:
                secondary_count = db.get_api_usage_last_hour(config.SECONDARY_PROVIDER or "secondary")
                self.ok_items.append(f"✅ {config.SECONDARY_PROVIDER} API: {secondary_count} calls/hour")
            
        except Exception as e:
            self.warnings.append(f"⚠️ API usage: {e}")
    
    def check_telegram_bot(self):
        """Telegram bot çalışıyor mu?"""
        try:
            import subprocess
            
            if sys.platform == "win32":
                cmd = 'wmic process where "name=\'python.exe\'" get commandline'
                res = subprocess.check_output(cmd, shell=True, text=True, errors="replace")
                bot_running = "telegram_bot.py" in res
            else:
                res = subprocess.check_output(["pgrep", "-f", "telegram_bot.py"], text=True)
                bot_running = bool(res.strip())
            
            if bot_running:
                self.ok_items.append("✅ Telegram bot: RUNNING")
            else:
                self.warnings.append("⚠️ Telegram bot: NOT RUNNING")
            
        except Exception:
            self.warnings.append("⚠️ Telegram bot: Durum bilinmiyor")
    
    def check_work_dir(self):
        """Work dizini temizliği"""
        try:
            work_dir = Path(config.WORK_DIR)
            if work_dir.exists():
                total_size = sum(f.stat().st_size for f in work_dir.rglob("*") if f.is_file()) / (1024 * 1024)
                
                if total_size > 500:
                    self.warnings.append(f"⚠️ Work dizini çok büyük: {total_size:.0f}MB (temizlik önerilir)")
                elif total_size > 100:
                    self.ok_items.append(f"✅ Work dir: {total_size:.0f}MB")
                else:
                    self.ok_items.append(f"✅ Work dir: OK ({total_size:.0f}MB)")
            else:
                self.ok_items.append("✅ Work dir: temiz")
        except Exception as e:
            self.warnings.append(f"⚠️ Work dir: {e}")
    
    def check_recent_activity(self):
        """Son tarama aktivitesi"""
        try:
            db = get_db()
            stats = db.get_stats()
            
            scans_7d = stats.get('scans_last_7_days', 0)
            
            if scans_7d == 0:
                self.warnings.append("⚠️ Son 7 günde tarama yok")
            else:
                self.ok_items.append(f"✅ Son 7 gün: {scans_7d} tarama")
            
        except Exception as e:
            self.warnings.append(f"⚠️ Recent activity: {e}")
    
    def run_all_checks(self):
        """Tüm kontrolleri çalıştır"""
        print("🏥 Sistem Sağlık Kontrolü")
        print("=" * 60)
        
        self.check_database()
        self.check_logs()
        self.check_disk_space()
        self.check_api_keys()
        self.check_api_usage()
        self.check_telegram_bot()
        self.check_work_dir()
        self.check_recent_activity()
        
        # Sonuçları yazdır
        print()
        if self.issues:
            print("❌ KRİTİK SORUNLAR:")
            for issue in self.issues:
                print(f"   {issue}")
            print()
        
        if self.warnings:
            print("⚠️  UYARILAR:")
            for warning in self.warnings:
                print(f"   {warning}")
            print()
        
        if self.ok_items:
            print("✅ SAĞLIKLI:")
            for ok in self.ok_items:
                print(f"   {ok}")
            print()
        
        print("=" * 60)
        
        # Genel durum
        if self.issues:
            print("🔴 DURUM: SORUN VAR - Müdahale gerekli!")
            return 2
        elif self.warnings:
            print("🟡 DURUM: UYARI - Dikkat gerekli")
            return 1
        else:
            print("🟢 DURUM: SAĞLIKLI - Tüm sistemler normal")
            return 0


def main():
    """Ana fonksiyon"""
    checker = HealthChecker()
    exit_code = checker.run_all_checks()
    
    print("\n💡 ÖNERİLER:")
    if checker.issues:
        print("   • Kritik sorunları çözün: .env kontrol, disk temizlik, vb.")
    if checker.warnings:
        print("   • VACUUM çalıştırın: python3 -c \"from database import get_db; get_db().vacuum()\"")
        print("   • Log temizliği: rm logs/*.log.* logs/*.jsonl.*")
        print("   • Work temizliği: rm -rf work/*")
    
    print("\n📊 Detaylı istatistik için:")
    print("   python3 -c \"from database import get_db; import json; print(json.dumps(get_db().get_stats(), indent=2))\"")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
