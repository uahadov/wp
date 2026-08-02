"""
Lightweight SQLite Database
===========================

1.5GB RAM friendly - SQLite (no server), connection pooling, indexes
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager


class VulnDatabase:
    """Hafif SQLite database (1.5GB RAM friendly)"""
    
    def __init__(self, db_path: str = "./scanner.db"):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Database ve tabloları oluştur"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Plugins table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plugins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT NOT NULL UNIQUE,
                    name TEXT,
                    version TEXT,
                    last_scanned_at TEXT,
                    scan_count INTEGER DEFAULT 0,
                    vulnerabilities_found INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Scans table (audit trail)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_id INTEGER,
                    version TEXT,
                    result TEXT,
                    vulnerability_count INTEGER DEFAULT 0,
                    taint_flows_found INTEGER DEFAULT 0,
                    scanned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds REAL,
                    FOREIGN KEY (plugin_id) REFERENCES plugins(id)
                )
            """)
            
            # Vulnerabilities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vulnerabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER,
                    plugin_slug TEXT,
                    vulnerability_type TEXT,
                    severity TEXT,
                    cvss_score REAL,
                    location TEXT,
                    vulnerable_code TEXT,
                    description TEXT,
                    poc_command TEXT,
                    wordfence_category TEXT,
                    verified_by_ai BOOLEAN DEFAULT 0,
                    verified_by_hakem BOOLEAN DEFAULT 0,
                    found_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scan_id) REFERENCES scans(id)
                )
            """)
            
            # API usage tracking (rate limit monitor)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT,
                    model TEXT,
                    success BOOLEAN,
                    tokens_used INTEGER DEFAULT 0,
                    rate_limited BOOLEAN DEFAULT 0,
                    called_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Manual Validations (FP Learning - v4.1)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS manual_validations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vuln_id INTEGER NOT NULL,
                    is_true_positive BOOLEAN NOT NULL,
                    reason TEXT,
                    validated_by TEXT,
                    validated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vuln_id) REFERENCES vulnerabilities(id)
                )
            """)
            
            # Indexes (performance)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_plugins_slug ON plugins(slug)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scans_plugin ON scans(plugin_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vulns_plugin ON vulnerabilities(plugin_slug)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vulns_severity ON vulnerabilities(severity)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_provider ON api_usage(provider, called_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_validations_vuln ON manual_validations(vuln_id)")
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Connection context manager (auto-close, thread-safe)"""
        # check_same_thread=False: Paralel tarama için gerekli
        # Her thread kendi connection'ını context manager ile alır (güvenli)
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Dict-like access
        try:
            yield conn
        finally:
            conn.close()
    
    def execute(self, query: str, params: tuple = None):
        """
        Genel SQL execute metodu (FP Learner için)
        
        Args:
            query: SQL query
            params: Query parametreleri
        
        Returns:
            SELECT için: List[Dict], INSERT için: lastrowid
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            conn.commit()
            
            # SELECT ise sonuçları döndür
            if query.strip().upper().startswith("SELECT"):
                return [dict(row) for row in cursor.fetchall()]
            
            # INSERT ise lastrowid
            return cursor.lastrowid
    
    # === PLUGIN OPERATIONS ===
    
    def is_plugin_scanned(self, slug: str, version: str) -> bool:
        """Plugin daha önce tarandı mı?"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM plugins 
                WHERE slug = ? AND version = ? AND last_scanned_at IS NOT NULL
            """, (slug, version))
            return cursor.fetchone() is not None
    
    def add_plugin_scan(self, slug: str, name: str, version: str, 
                       result: str, vuln_count: int, taint_flows: int, 
                       duration: float) -> int:
        """Plugin tarama sonucunu kaydet"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Plugin ekle veya güncelle
            cursor.execute("""
                INSERT INTO plugins (slug, name, version, last_scanned_at, scan_count, vulnerabilities_found)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    version = excluded.version,
                    last_scanned_at = excluded.last_scanned_at,
                    scan_count = scan_count + 1,
                    vulnerabilities_found = vulnerabilities_found + excluded.vulnerabilities_found
            """, (slug, name, version, datetime.now().isoformat(), vuln_count))
            
            plugin_id = cursor.lastrowid
            if plugin_id == 0:  # Conflict oldu, id'yi al
                cursor.execute("SELECT id FROM plugins WHERE slug = ?", (slug,))
                plugin_id = cursor.fetchone()['id']
            
            # Scan kaydı ekle
            cursor.execute("""
                INSERT INTO scans (plugin_id, version, result, vulnerability_count, 
                                 taint_flows_found, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (plugin_id, version, result, vuln_count, taint_flows, duration))
            
            scan_id = cursor.lastrowid
            conn.commit()
            return scan_id
    
    def add_vulnerability(self, scan_id: int, plugin_slug: str, vuln: Dict):
        """Zafiyet kaydet"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vulnerabilities 
                (scan_id, plugin_slug, vulnerability_type, severity, cvss_score,
                 location, vulnerable_code, description, poc_command, 
                 wordfence_category, verified_by_ai, verified_by_hakem)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """, (
                scan_id,
                plugin_slug,
                vuln.get('type', 'Unknown'),
                vuln.get('severity', 'High'),
                vuln.get('cvss_score', 0.0),
                vuln.get('location', ''),
                vuln.get('vulnerable_code', '')[:500],  # Limit to 500 chars
                vuln.get('description', '')[:1000],
                vuln.get('poc_command', ''),
                vuln.get('wordfence_category', ''),
                vuln.get('verified_by_hakem', False)
            ))
            conn.commit()
    
    # === API TRACKING ===
    
    def log_api_call(self, provider: str, model: str, success: bool, 
                     tokens: int = 0, rate_limited: bool = False):
        """API çağrısını kaydet"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO api_usage (provider, model, success, tokens_used, rate_limited)
                VALUES (?, ?, ?, ?, ?)
            """, (provider, model, success, tokens, rate_limited))
            conn.commit()
    
    def get_api_usage_last_hour(self, provider: str) -> int:
        """Son 1 saatteki API çağrı sayısı"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM api_usage
                WHERE provider = ? 
                AND datetime(called_at) > datetime('now', '-1 hour')
            """, (provider,))
            return cursor.fetchone()['count']
    
    def get_rate_limit_count_today(self, provider: str) -> int:
        """Bugün kaç kez rate limit yedik?"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM api_usage
                WHERE provider = ? AND rate_limited = 1
                AND date(called_at) = date('now')
            """, (provider,))
            return cursor.fetchone()['count']
    
    # === STATISTICS ===
    
    def get_stats(self) -> Dict:
        """Genel istatistikler"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total plugins scanned
            cursor.execute("SELECT COUNT(*) as count FROM plugins")
            total_plugins = cursor.fetchone()['count']
            
            # Total vulnerabilities
            cursor.execute("SELECT COUNT(*) as count FROM vulnerabilities")
            total_vulns = cursor.fetchone()['count']
            
            # Vulnerabilities by severity
            cursor.execute("""
                SELECT severity, COUNT(*) as count 
                FROM vulnerabilities 
                GROUP BY severity
            """)
            by_severity = {row['severity']: row['count'] for row in cursor.fetchall()}
            
            # Last 7 days scans
            cursor.execute("""
                SELECT COUNT(*) as count FROM scans
                WHERE date(scanned_at) >= date('now', '-7 days')
            """)
            scans_last_7_days = cursor.fetchone()['count']
            
            # API usage today
            cursor.execute("""
                SELECT provider, COUNT(*) as count 
                FROM api_usage
                WHERE date(called_at) = date('now')
                GROUP BY provider
            """)
            api_usage_today = {row['provider']: row['count'] for row in cursor.fetchall()}
            
            return {
                "total_plugins_scanned": total_plugins,
                "total_vulnerabilities_found": total_vulns,
                "vulnerabilities_by_severity": by_severity,
                "scans_last_7_days": scans_last_7_days,
                "api_usage_today": api_usage_today
            }
    
    def get_recent_vulnerabilities(self, limit: int = 10) -> List[Dict]:
        """Son bulunan zafiyetler"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    v.plugin_slug,
                    v.vulnerability_type,
                    v.severity,
                    v.cvss_score,
                    v.location,
                    v.found_at
                FROM vulnerabilities v
                ORDER BY v.found_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # === MAINTENANCE ===
    
    def vacuum(self):
        """Database optimize (disk space recover)"""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
    
    def get_database_size(self) -> float:
        """Database boyutu (MB)"""
        if self.db_path.exists():
            return self.db_path.stat().st_size / (1024 * 1024)
        return 0.0


# Global singleton
_db_instance = None

def get_db() -> VulnDatabase:
    """Global database instance (singleton - hafif)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = VulnDatabase()
    return _db_instance
