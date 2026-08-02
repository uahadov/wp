"""
Lightweight Logging System
==========================

1.5GB RAM friendly - rotating file logs, structured JSON logging
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
import sys


class StructuredLogger:
    """Hafif, structured logging sistemi (JSON + human-readable)"""
    
    def __init__(self, name: str = "scanner", log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Main logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()  # Clear existing handlers
        
        # Console handler (human-readable, INFO+)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (detailed, DEBUG+, rotating 10MB max)
        file_handler = RotatingFileHandler(
            self.log_dir / "scanner.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,  # Keep 3 old logs (max 30MB total)
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # JSON audit log (structured, rotating 5MB max)
        self.audit_handler = RotatingFileHandler(
            self.log_dir / "audit.jsonl",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=2,  # Max 10MB
            encoding='utf-8'
        )
        self.audit_handler.setLevel(logging.INFO)
    
    def _write_audit(self, event_type: str, data: dict):
        """Audit log'a JSON yaz (JSONL format - her satır bir JSON)"""
        try:
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                **data
            }
            self.audit_handler.stream.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
            self.audit_handler.stream.flush()
        except Exception as e:
            self.logger.warning(f"Audit log yazma hatası: {e}")
    
    # === PUBLIC API ===
    
    def debug(self, msg: str):
        """Debug log (sadece file'a)"""
        self.logger.debug(msg)
    
    def info(self, msg: str):
        """Info log (console + file)"""
        self.logger.info(msg)
    
    def warning(self, msg: str):
        """Warning log"""
        self.logger.warning(msg)
    
    def error(self, msg: str, exc_info=False):
        """Error log"""
        self.logger.error(msg, exc_info=exc_info)
    
    def critical(self, msg: str):
        """Critical log"""
        self.logger.critical(msg)
    
    # === AUDIT EVENTS ===
    
    def audit_scan_start(self, plugin_count: int, strategy: str = "default"):
        """Tarama başladı"""
        self.info(f"🚀 Tarama başladı: {plugin_count} plugin, strateji: {strategy}")
        self._write_audit("scan_start", {
            "plugin_count": plugin_count,
            "strategy": strategy
        })
    
    def audit_scan_complete(self, total_scanned: int, vulns_found: int, duration_sec: float):
        """Tarama tamamlandı"""
        self.info(f"✅ Tarama tamamlandı: {total_scanned} plugin, {vulns_found} zafiyet, {duration_sec:.1f}s")
        self._write_audit("scan_complete", {
            "total_scanned": total_scanned,
            "vulnerabilities_found": vulns_found,
            "duration_seconds": duration_sec
        })
    
    def audit_plugin_scan(self, plugin_slug: str, version: str, result: str, vuln_count: int = 0):
        """Plugin tarandı"""
        self.debug(f"Plugin tarandı: {plugin_slug} v{version} → {result} ({vuln_count} zafiyet)")
        self._write_audit("plugin_scan", {
            "plugin_slug": plugin_slug,
            "version": version,
            "result": result,
            "vulnerability_count": vuln_count
        })
    
    def audit_vulnerability_found(self, plugin_slug: str, vuln_type: str, severity: str, cvss: float):
        """Zafiyet bulundu"""
        self.info(f"🚨 ZAFİYET: {plugin_slug} → {vuln_type} ({severity}, CVSS: {cvss})")
        self._write_audit("vulnerability_found", {
            "plugin_slug": plugin_slug,
            "vulnerability_type": vuln_type,
            "severity": severity,
            "cvss_score": cvss
        })
    
    def audit_api_call(self, provider: str, model: str, success: bool, tokens: int = 0):
        """API çağrısı"""
        self.debug(f"API: {provider}/{model} → {'✓' if success else '✗'} ({tokens} tokens)")
        self._write_audit("api_call", {
            "provider": provider,
            "model": model,
            "success": success,
            "tokens_used": tokens
        })
    
    def audit_rate_limit(self, service: str, retry_after: int):
        """Rate limit hit"""
        self.warning(f"⏳ Rate limit: {service} → {retry_after}s bekleniyor")
        self._write_audit("rate_limit_hit", {
            "service": service,
            "retry_after_seconds": retry_after
        })
    
    def audit_error(self, error_type: str, message: str, plugin_slug: str = None):
        """Hata oluştu"""
        self.error(f"❌ {error_type}: {message}" + (f" (plugin: {plugin_slug})" if plugin_slug else ""))
        self._write_audit("error", {
            "error_type": error_type,
            "message": message,
            "plugin_slug": plugin_slug
        })


# Global singleton instance
_logger_instance = None

def get_logger(name: str = "scanner") -> StructuredLogger:
    """Global logger instance al (singleton pattern - hafif)"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger(name)
    return _logger_instance


# Convenience functions
def debug(msg: str):
    get_logger().debug(msg)

def info(msg: str):
    get_logger().info(msg)

def warning(msg: str):
    get_logger().warning(msg)

def error(msg: str, exc_info=False):
    get_logger().error(msg, exc_info=exc_info)

def critical(msg: str):
    get_logger().critical(msg)
