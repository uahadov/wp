"""
Progress Tracker
================

Tarama ilerlemesini takip et ve raporla (thread-safe)
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional


class ProgressTracker:
    """Tarama ilerleme takibi (1.5GB RAM friendly, thread-safe)"""
    
    def __init__(self):
        self._lock = threading.Lock()  # Thread safety için
        self.reset()
    
    def reset(self):
        """Takibi sıfırla"""
        with self._lock:
            self.start_time = None
            self.total_batches = 0
            self.current_batch = 0
            self.plugins_per_batch = 0
            self.current_plugin_index = 0
            self.current_plugin_name = ""
            self.current_plugin_version = ""
            self.current_status = "Idle"
            self.total_scanned = 0
            self.total_vulns_found = 0
            self.last_update_time = None
    
    def start_scan(self, total_batches: int, plugins_per_batch: int):
        """Taramayı başlat"""
        with self._lock:
            self.start_time = time.time()
            self.total_batches = total_batches
            self.plugins_per_batch = plugins_per_batch
            self.current_batch = 0
            self.last_update_time = time.time()
    
    def start_batch(self, batch_number: int):
        """Yeni batch başladı"""
        with self._lock:
            self.current_batch = batch_number
            self.current_plugin_index = 0
            self.current_status = f"Batch #{batch_number} başlatılıyor..."
            self.last_update_time = time.time()
    
    def update_plugin(self, index: int, name: str, version: str):
        """Şu anki plugin bilgisi"""
        with self._lock:
            self.current_plugin_index = index
            self.current_plugin_name = name
            self.current_plugin_version = version
            self.current_status = "Plugin indiriliyor..."
            self.last_update_time = time.time()
    
    def update_status(self, status: str):
        """Durum güncelle"""
        with self._lock:
            self.current_status = status
            self.last_update_time = time.time()
    
    def increment_scanned(self):
        """Taranan plugin sayısını artır (thread-safe)"""
        with self._lock:
            self.total_scanned += 1
    
    def increment_vulns(self):
        """Bulunan zafiyet sayısını artır (thread-safe)"""
        with self._lock:
            self.total_vulns_found += 1
    
    def get_elapsed_time(self) -> float:
        """Geçen süre (saniye)"""
        with self._lock:
            if self.start_time is None:
                return 0.0
            return time.time() - self.start_time
    
    def get_estimated_remaining_time(self) -> Optional[float]:
        """Tahmini kalan süre (saniye, thread-safe)"""
        with self._lock:
            if self.start_time is None or self.total_scanned == 0:
                return None
            
            elapsed = time.time() - self.start_time
            avg_time_per_plugin = elapsed / self.total_scanned
            
            # Kalan plugin tahmini
            total_estimated_plugins = self.total_batches * self.plugins_per_batch
            remaining_plugins = total_estimated_plugins - self.total_scanned
            
            if remaining_plugins <= 0:
                return 0.0
            
            return avg_time_per_plugin * remaining_plugins
    
    def get_progress_percentage(self) -> float:
        """İlerleme yüzdesi (thread-safe)"""
        with self._lock:
            if self.total_batches == 0:
                return 0.0
            
            # Batch bazlı ilerleme
            batch_progress = (self.current_batch / self.total_batches) * 100
            
            # Plugin bazlı ilerleme (mevcut batch içinde)
            if self.plugins_per_batch > 0 and self.current_plugin_index > 0:
                plugin_progress = (self.current_plugin_index / self.plugins_per_batch) / self.total_batches * 100
                return min(100.0, batch_progress + plugin_progress)
            
            return min(100.0, batch_progress)
    
    def format_time(self, seconds: float) -> str:
        """Saniyeyi okunabilir formata çevir"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}dk {int(seconds % 60)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}sa {minutes}dk"
    
    def get_progress_report(self) -> str:
        """İlerleme raporu (Telegram için, thread-safe, deadlock-free)"""
        # Tüm değerleri tek lock'ta al (deadlock önleme)
        with self._lock:
            if self.start_time is None:
                elapsed = 0.0
            else:
                elapsed = time.time() - self.start_time
            
            # Kalan süre hesapla
            if self.start_time is None or self.total_scanned == 0:
                remaining = None
            else:
                avg_time = elapsed / self.total_scanned
                total_est = self.total_batches * self.plugins_per_batch
                remaining_plugins = total_est - self.total_scanned
                remaining = avg_time * remaining_plugins if remaining_plugins > 0 else 0.0
            
            # Progress yüzdesi
            if self.total_batches == 0:
                progress_pct = 0.0
            else:
                batch_progress = (self.current_batch / self.total_batches) * 100
                if self.plugins_per_batch > 0 and self.current_plugin_index > 0:
                    plugin_progress = (self.current_plugin_index / self.plugins_per_batch) / self.total_batches * 100
                    progress_pct = min(100.0, batch_progress + plugin_progress)
                else:
                    progress_pct = min(100.0, batch_progress)
            
            # Copy values for use outside lock
            current_batch = self.current_batch
            total_batches = self.total_batches
            current_plugin_index = self.current_plugin_index
            plugins_per_batch = self.plugins_per_batch
            current_plugin_name = self.current_plugin_name
            current_plugin_version = self.current_plugin_version
            current_status = self.current_status
            total_scanned = self.total_scanned
            total_vulns_found = self.total_vulns_found
        
        # Report oluştur (lock dışında)
        bar_length = 10
        filled = int(bar_length * progress_pct / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        
        report = (
            f"📊 <b>TARAMA İLERLEMESİ</b>\n"
            f"{'━' * 25}\n"
            f"🔄 <b>Batch:</b> {current_batch}/{total_batches}\n"
            f"📦 <b>Plugin:</b> {current_plugin_index}/{plugins_per_batch}"
        )
        
        if current_plugin_name:
            report += f" ({current_plugin_name} v{current_plugin_version})\n"
        else:
            report += "\n"
        
        report += (
            f"🔬 <b>Durum:</b> {current_status}\n"
            f"⏱️ <b>Geçen:</b> {self.format_time(elapsed)}\n"
        )
        
        if remaining is not None and remaining > 0:
            report += f"📈 <b>Tahmini Kalan:</b> {self.format_time(remaining)}\n"
        
        report += (
            f"\n{bar} {progress_pct:.0f}%\n"
            f"\n📊 <b>İstatistik:</b>\n"
            f"   • Taranan: {total_scanned}\n"
            f"   • Zafiyet: {total_vulns_found}\n"
            f"{'━' * 25}"
        )
        
        return report
    
    def get_simple_status(self) -> str:
        """Basit durum (console için, thread-safe, deadlock-free)"""
        with self._lock:
            # Progress yüzdesi hesapla (deadlock önleme için inline)
            if self.total_batches == 0:
                progress_pct = 0.0
            else:
                batch_progress = (self.current_batch / self.total_batches) * 100
                if self.plugins_per_batch > 0 and self.current_plugin_index > 0:
                    plugin_progress = (self.current_plugin_index / self.plugins_per_batch) / self.total_batches * 100
                    progress_pct = min(100.0, batch_progress + plugin_progress)
                else:
                    progress_pct = min(100.0, batch_progress)
            
            return (
                f"[Batch {self.current_batch}/{self.total_batches}] "
                f"[{self.current_plugin_index}/{self.plugins_per_batch}] "
                f"({progress_pct:.0f}%) - {self.current_status}"
            )


# Global singleton
_tracker_instance = None

def get_tracker() -> ProgressTracker:
    """Global progress tracker (singleton)"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ProgressTracker()
    return _tracker_instance
