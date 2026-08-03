"""
╔══════════════════════════════════════════════════════════════════════╗
║   WP-CVEHunter v3.1 · WordPress Plugin Vulnerability Hunter          ║
║   Unauthenticated & Low-Privilege Real Vulnerabilities Only          ║
║   Taint Tracking · Smart Sanitization Filter · Parallel Engine       ║
║   Scan Caching & REST API Route Analyzer & Auto-PoC Generator        ║
╚══════════════════════════════════════════════════════════════════════╝

YASAL UYARI: Bu araç yalnızca sorumlu güvenlik araştırması (responsible
disclosure) amaçlıdır. Yetkisiz sistemlerde kullanmak yasaktır.
"""

import os
import re
import sys
import json
import time
import zipfile
import hashlib
import logging
import tempfile
import textwrap
import warnings
import threading
import argparse
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

# Kütüphanelerden gelen zararsız uyarıları (FutureWarning vb.) terminalde gizler
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ── Dependency checks ─────────────────────────────────────────────────────────
try:
    import requests
    from requests.exceptions import RequestException, Timeout
except ImportError:
    print("[!] pip install requests")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.live import Live
    from rich.layout import Layout
    from rich.progress import (
        Progress, SpinnerColumn, TextColumn, BarColumn,
        MofNCompleteColumn, TimeElapsedColumn,
    )
    from rich.prompt import Prompt, IntPrompt, Confirm
    from rich import box
    from rich.markup import escape as rich_escape
    from rich.padding import Padding
    from rich.text import Text
except ImportError:
    print("[!] pip install rich")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS & DATABASE
# ══════════════════════════════════════════════════════════════════════════════

TOOL_NAME    = "WP-CVEHunter"
TOOL_VERSION = "3.1.0"

WP_API_BASE      = "https://api.wordpress.org/plugins/info/1.2/"
WP_DOWNLOAD_BASE = "https://downloads.wordpress.org/plugin/"

REPORTABLE_VULN_TYPES = {
    "SQL Injection",
    "Reflected XSS",
    "Stored XSS",
    "CSRF",
    "LFI",
    "RCE",
    "SSRF",
    "Open Redirect",
    "Privilege Escalation",
    "Arbitrary File Upload",
    "Insecure Deserialization",
    "Auth Bypass / Missing Authorization",
}

ADMIN_CONTEXT_PATTERNS = [
    r"current_user_can\s*\(\s*['\"]manage_options['\"]",
    r"current_user_can\s*\(\s*['\"]administrator['\"]",
    r"check_admin_referer\s*\(",
    r"admin_menu",
    r"add_options_page",
    r"add_menu_page",
]

OUTPUT_DIR = Path("wp_cve_hunter_output")
CACHE_FILE = OUTPUT_DIR / "scanned_plugins.json"

console = Console(highlight=False)

logger = logging.getLogger("WPCVEHunter")
logger.setLevel(logging.DEBUG)
_fh = logging.FileHandler("wp_cve_hunter.log", encoding="utf-8")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
logger.addHandler(_fh)

# ══════════════════════════════════════════════════════════════════════════════
#  SEVERITY / CONFIDENCE
# ══════════════════════════════════════════════════════════════════════════════

class Severity:
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"

class Confidence:
    CONFIRMED = "CONFIRMED"
    HIGH      = "HIGH"
    MEDIUM    = "MEDIUM"
    LOW       = "LOW"

SEV_COLOR = {
    Severity.CRITICAL: "bold white on red",
    Severity.HIGH:     "bold red",
    Severity.MEDIUM:   "bold yellow",
    Severity.LOW:      "cyan",
}
CONF_COLOR = {
    Confidence.CONFIRMED: "bold green",
    Confidence.HIGH:      "green",
    Confidence.MEDIUM:    "yellow",
    Confidence.LOW:       "dim",
}

CWE_MAP = {
    "SQL Injection":                        ("CWE-89",  9.8),
    "Reflected XSS":                        ("CWE-79",  6.1),
    "Stored XSS":                           ("CWE-79",  8.8),
    "CSRF":                                 ("CWE-352", 8.8),
    "LFI":                                  ("CWE-22",  9.8),
    "RCE":                                  ("CWE-94",  9.8),
    "SSRF":                                 ("CWE-918", 8.6),
    "Open Redirect":                        ("CWE-601", 6.1),
    "Privilege Escalation":                 ("CWE-269", 8.8),
    "Arbitrary File Upload":                ("CWE-434", 9.8),
    "Insecure Deserialization":             ("CWE-502", 9.8),
    "Auth Bypass / Missing Authorization":  ("CWE-862", 8.5),
}


# ══════════════════════════════════════════════════════════════════════════════
#  SCAN HISTORY / CACHE MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class ScanCacheManager:
    """Tekrarlı taramaları önlemek için taranan pluginleri saklayan hafıza/cache sınıfı."""
    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.scanned_database: Dict[str, str] = self._load_cache()

    def _load_cache(self) -> Dict[str, str]:
        with self.lock:
            if self.cache_file.exists():
                try:
                    with open(self.cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data if isinstance(data, dict) else {}
                except Exception as e:
                    logger.error(f"Hafıza dosyası yüklenirken hata oluştu: {e}")
                    return {}
            return {}

    def is_scanned(self, slug: str, version: str) -> bool:
        """Plugin daha önce bu versiyonu ile taranmış mı?"""
        with self.lock:
            return self.scanned_database.get(slug) == version

    def mark_as_scanned(self, slug: str, version: str):
        """Plugini taranmış olarak veritabanına kaydet."""
        with self.lock:
            self.scanned_database[slug] = version
            try:
                # Olası kilitlenmeleri önlemek için geçici dosyaya yazıp taşımak daha güvenlidir
                temp_file = self.cache_file.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(self.scanned_database, f, indent=4)
                os.replace(temp_file, self.cache_file)
            except Exception as e:
                logger.error(f"Hafıza dosyası güncellenirken hata oluştu: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  RISK SCORER
# ══════════════════════════════════════════════════════════════════════════════

RISK_TAGS = {
    "form": 8, "upload": 12, "redirect": 8, "ajax": 8,
    "file": 10, "import": 10, "export": 6, "rest": 8,
    "api": 6, "contact": 6, "admin": 5, "shortcode": 6,
    "widget": 4, "email": 5, "search": 7, "filter": 6,
}

def compute_risk_score(plugin: Dict) -> int:
    score = 0
    last_updated_str = plugin.get("last_updated", "")
    try:
        lu = datetime.strptime(last_updated_str[:10], "%Y-%m-%d")
        days_old = (datetime.now() - lu).days
        if days_old > 365:
            score += 35
        elif days_old > 180:
            score += 20
    except Exception:
        score += 15

    installs = plugin.get("active_installs", 0)
    if installs >= 10_000:
        score += 20
    elif installs >= 1_000:
        score += 15

    tags = plugin.get("tags", {})
    tag_list = list(tags.values()) if isinstance(tags, dict) else tags
    for tag in tag_list:
        for r_tag, pts in RISK_TAGS.items():
            if r_tag in tag.lower():
                score += pts
                break
    return min(score, 100)

# ══════════════════════════════════════════════════════════════════════════════
#  TAINT & SANITIZATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class PHPFileScope:
    def __init__(self, content: str):
        self.content = content
        self.lines = content.splitlines()
        self.tainted_vars: Set[str] = set()
        self.variable_assignments: Dict[str, str] = {}
        self._trace_taints()

    def _trace_taints(self):
        user_sources = [r"\$_GET", r"\$_POST", r"\$_REQUEST", r"\$_COOKIE", r"\$_FILES"]
        
        for line in self.lines:
            match = re.search(r"(\$[a-zA-Z0-9_]+)\s*=\s*(.+?);", line)
            if match:
                var_name = match.group(1)
                value_expr = match.group(2)
                self.variable_assignments[var_name] = value_expr

                if any(re.search(src, value_expr) for src in user_sources):
                    self.tainted_vars.add(var_name)
                elif any(t_var in value_expr for t_var in self.tainted_vars):
                    self.tainted_vars.add(var_name)

    def is_expr_tainted(self, expr: str) -> bool:
        user_sources = ["$_GET", "$_POST", "$_REQUEST", "$_COOKIE", "$_FILES"]
        if any(src in expr for src in user_sources):
            return True
        return any(t_var in expr for t_var in self.tainted_vars)


# ══════════════════════════════════════════════════════════════════════════════
#  PHP STATIC ANALYSIS MOTORU (SAST)
# ══════════════════════════════════════════════════════════════════════════════

class Finding:
    def __init__(self, vuln_type: str, file_path: str, line_no: int,
                 line_content: str, severity: str, confidence: str,
                 context_lines: List[str] = None, is_admin_context: bool = False,
                 rest_route: str = ""):
        self.vuln_type       = vuln_type
        self.file_path       = file_path
        self.line_no         = line_no
        self.line_content    = line_content.strip()
        self.severity        = severity
        self.confidence      = confidence
        self.context_lines   = context_lines or []
        self.is_admin_context = is_admin_context
        self.rest_route      = rest_route
        cwe, cvss           = CWE_MAP.get(vuln_type, ("CWE-Unknown", 5.0))
        self.cwe             = cwe
        self.cvss_estimate   = cvss if not is_admin_context else cvss * 0.5


class PHPStaticAnalyzer:
    def __init__(self):
        self.safe_funcs = [
            "esc_sql", "absint", "intval", "floatval", "esc_attr", 
            "esc_html", "sanitize_key", "sanitize_title", "prepare(",
            "wp_verify_nonce", "check_admin_referer", "check_ajax_referer"
        ]

    def _get_context(self, lines: List[str], idx: int, window: int = 8) -> List[str]:
        start = max(0, idx - window)
        end   = min(len(lines), idx + window + 1)
        return lines[start:end]

    def _is_admin_context(self, context_lines: List[str]) -> bool:
        combined = " ".join(context_lines).lower()
        return any(re.search(pat, combined) for pat in ADMIN_CONTEXT_PATTERNS)

    def _is_sanitized(self, line: str, context: List[str]) -> bool:
        combined = " ".join(context) + " " + line
        return any(s in combined for s in self.safe_funcs)

    def analyze_file(self, filepath: Path) -> List[Finding]:
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        scope = PHPFileScope(content)
        findings: List[Finding] = []

        for idx, line in enumerate(scope.lines):
            ctx = self._get_context(scope.lines, idx)
            is_admin = self._is_admin_context(ctx)
            is_sanitized = self._is_sanitized(line, ctx)

            # 1. SQLi Tespiti
            if any(term in line for term in ["$wpdb->query", "$wpdb->get_results", "$wpdb->get_var", "$wpdb->get_row"]):
                if scope.is_expr_tainted(line) and not is_sanitized and "prepare" not in line:
                    findings.append(Finding(
                        "SQL Injection", str(filepath), idx + 1, line,
                        Severity.CRITICAL if not is_admin else Severity.MEDIUM,
                        Confidence.CONFIRMED, ctx, is_admin
                    ))

            # 2. XSS Tespiti
            if any(term in line for term in ["echo ", "print ", "printf", "<?="]):
                if scope.is_expr_tainted(line) and not is_sanitized:
                    if not any(k in line for k in ["wp_kses", "esc_"]):
                        is_stored = any(s in " ".join(ctx) for s in ["insert", "update", "add_post_meta", "update_option"])
                        findings.append(Finding(
                            "Stored XSS" if is_stored else "Reflected XSS", str(filepath), idx + 1, line,
                            Severity.HIGH if not is_admin else Severity.MEDIUM,
                            Confidence.CONFIRMED, ctx, is_admin
                        ))

            # 3. CSRF & Auth Bypass / Missing Authorization AJAX Tespiti
            if "add_action" in line and ("wp_ajax_nopriv_" in line or "wp_ajax_" in line):
                ctx_str = " ".join(ctx).lower()
                has_nonce = any(n in ctx_str for n in ["wp_verify_nonce", "check_ajax_referer", "check_admin_referer"])
                has_auth  = any(a in ctx_str for a in ["current_user_can", "is_user_logged_in"])
                
                if "wp_ajax_nopriv_" in line and (not has_nonce or not has_auth):
                    findings.append(Finding(
                        "Auth Bypass / Missing Authorization", str(filepath), idx + 1, line,
                        Severity.HIGH, Confidence.HIGH, ctx, False
                    ))
                elif "wp_ajax_" in line and not has_nonce and not has_auth:
                    findings.append(Finding(
                        "CSRF", str(filepath), idx + 1, line,
                        Severity.MEDIUM, Confidence.MEDIUM, ctx, is_admin
                    ))

            # 4. REST API Yetki Analizcisi (register_rest_route)
            if "register_rest_route" in line:
                ctx_str = " ".join(ctx)
                is_callback_missing = "permission_callback" not in ctx_str
                is_callback_true    = any(tc in ctx_str for tc in ["__return_true", "permission_callback' => '__return_true'", '"permission_callback" => "__return_true"'])
                
                if is_callback_missing or is_callback_true:
                    route_name = "Bilinmeyen Rota"
                    route_match = re.search(r"register_rest_route\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]", line)
                    if route_match:
                        route_name = f"/wp-json/{route_match.group(1)}/{route_match.group(2)}"
                    
                    findings.append(Finding(
                        "Auth Bypass / Missing Authorization", str(filepath), idx + 1, line,
                        Severity.HIGH, Confidence.CONFIRMED, ctx, False, rest_route=route_name
                    ))

            # 5. LFI / Path Traversal
            if any(term in line for term in ["include", "require", "file_get_contents", "readfile"]) and scope.is_expr_tainted(line):
                if not any(safe in line for safe in ["realpath", "basename", "plugin_dir_path", "validate_file"]):
                    findings.append(Finding(
                        "LFI", str(filepath), idx + 1, line,
                        Severity.CRITICAL if not is_admin else Severity.MEDIUM,
                        Confidence.CONFIRMED, ctx, is_admin
                    ))

            # 6. RCE
            if any(term in line for term in ["eval(", "system(", "exec(", "shell_exec(", "passthru("]) and scope.is_expr_tainted(line):
                findings.append(Finding(
                    "RCE", str(filepath), idx + 1, line,
                    Severity.CRITICAL, Confidence.CONFIRMED, ctx, is_admin
                ))

            # 7. SSRF
            if any(term in line for term in ["wp_remote_get", "wp_remote_post", "curl_exec"]) and scope.is_expr_tainted(line):
                if not is_sanitized:
                    findings.append(Finding(
                        "SSRF", str(filepath), idx + 1, line,
                        Severity.HIGH if not is_admin else Severity.MEDIUM,
                        Confidence.HIGH, ctx, is_admin
                    ))

            # 8. Arbitrary File Upload
            if "move_uploaded_file" in line or "wp_handle_upload" in line:
                ctx_str = " ".join(ctx).lower()
                has_validation = any(v in ctx_str for v in ["wp_check_filetype", "allowed_mime_types", "mime_content_type"])
                if not has_validation:
                    findings.append(Finding(
                        "Arbitrary File Upload", str(filepath), idx + 1, line,
                        Severity.CRITICAL if not is_admin else Severity.HIGH,
                        Confidence.HIGH, ctx, is_admin
                    ))

        return findings


# ══════════════════════════════════════════════════════════════════════════════
#  PLUGIN DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════

class PluginDiscovery:
    def __init__(self, session: requests.Session, min_installs: int = 100, risk_threshold: int = 40):
        self.session = session
        self.min_installs = min_installs
        self.risk_threshold = risk_threshold
        self._seen_slugs: Set[str] = set()

    def fetch_page(self, page: int, search: str = "") -> List[Dict]:
        params = {
            "action": "query_plugins",
            "request[page]": page,
            "request[per_page]": 60,
            "request[fields][active_installs]": 1,
            "request[fields][last_updated]": 1,
            "request[fields][tags]": 1,
            "request[fields][tested]": 1,
            "request[fields][rating]": 1,
            "request[fields][requires_php]": 1,
            "request[fields][download_link]": 1,
        }
        if search:
            params["request[search]"] = search
        try:
            resp = self.session.get(WP_API_BASE, params=params, timeout=20)
            resp.raise_for_status()
            return resp.json().get("plugins", [])
        except Exception as e:
            logger.error(f"WordPress.org API sorgu hatası (Sayfa: {page}): {e}")
            return []

    def stream_candidates(self, search_terms: List[str] = None):
        if search_terms is None:
            search_terms = ["contact form", "upload", "redirect", "ajax", "import", "rest api", "gallery", "booking"]
        for term in search_terms:
            page = 1
            while True:
                plugins = self.fetch_page(page, search=term)
                if not plugins:
                    break
                for p in plugins:
                    slug = p.get("slug", "")
                    if not slug or slug in self._seen_slugs:
                        continue
                    if p.get("active_installs", 0) < self.min_installs:
                        continue
                    score = compute_risk_score(p)
                    p["_risk_score"] = score
                    if score >= self.risk_threshold:
                        self._seen_slugs.add(slug)
                        yield p
                page += 1
                if page > 10:  # Sayfalama güvenlik sınırı
                    break
                time.sleep(0.3)


# ══════════════════════════════════════════════════════════════════════════════
#  DOWNLOADER & EXTRACTOR
# ══════════════════════════════════════════════════════════════════════════════

class PluginDownloader:
    def __init__(self, session: requests.Session, work_dir: Path):
        self.session = session
        self.work_dir = work_dir
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def download_and_extract(self, plugin: Dict) -> Optional[Path]:
        slug    = plugin.get("slug", "")
        version = plugin.get("version", "")
        dl_link = plugin.get("download_link", f"{WP_DOWNLOAD_BASE}{slug}.{version}.zip")
        extract_dir = self.work_dir / slug
        if extract_dir.exists():
            return extract_dir

        zip_path = self.work_dir / f"{slug}.zip"
        try:
            resp = self.session.get(dl_link, timeout=40, stream=True)
            if resp.status_code != 200:
                return None
            with open(zip_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Bozuk/Yarım kalmış ZIP dosyası hatası için try-except koruması
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
            
            zip_path.unlink(missing_ok=True)
            return extract_dir
        except (zipfile.BadZipFile, Exception) as e:
            logger.error(f"ZIP çıkarma hatası veya bozuk dosya [{slug}]: {e}")
            zip_path.unlink(missing_ok=True)
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
            return None


# ══════════════════════════════════════════════════════════════════════════════
#  AUTO POC GENERATOR & REPORTS
# ══════════════════════════════════════════════════════════════════════════════

class CVEReportGenerator:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def _generate_poc_template(self, slug: str, finding: Finding) -> str:
        cwe, _ = CWE_MAP.get(finding.vuln_type, ("CWE-Unknown", 5.0))
        
        poc_steps = ""
        poc_http  = ""

        if finding.vuln_type == "SQL Injection":
            poc_steps = textwrap.dedent(f"""
            1. Hedef web uygulamasında zafiyetli url/endpoint'i tespit edin.
            2. Parametreye SQL enjeksiyon payload'u (örneğin tek tırnak ' veya sqlmap) ekleyin.
            3. Aşağıdaki HTTP isteğini gönderin.
            """)
            poc_http = textwrap.dedent(f"""
            GET /wp-content/plugins/{slug}/[dosya_yolu]?parametre=1' OR (SELECT 1 FROM (SELECT(SLEEP(5)))x)-- - HTTP/1.1
            Host: target.local
            User-Agent: Mozilla/5.0
            Connection: close
            """)
        elif "XSS" in finding.vuln_type:
            poc_steps = textwrap.dedent(f"""
            1. Zararlı JavaScript payload'unu parametre üzerinden gönderin.
            2. Kurban sayfayı açtığında script çalışacaktır.
            """)
            poc_http = textwrap.dedent(f"""
            GET /wp-content/plugins/{slug}/[dosya_yolu]?parametre="><script>alert(document.domain)</script> HTTP/1.1
            Host: target.local
            User-Agent: Mozilla/5.0
            Connection: close
            """)
        elif finding.vuln_type == "LFI":
            poc_steps = textwrap.dedent(f"""
            1. Dosya okuma parametresini directory traversal karakterleri ile değiştirin.
            2. Yerel sistem dosyaları yanıtta görüntülenecektir.
            """)
            poc_http = textwrap.dedent(f"""
            GET /wp-content/plugins/{slug}/[dosya_yolu]?parametre=../../../../etc/passwd HTTP/1.1
            Host: target.local
            User-Agent: Mozilla/5.0
            Connection: close
            """)
        elif "Auth Bypass" in finding.vuln_type:
            poc_steps = textwrap.dedent(f"""
            1. Eklentinin kaydettiği yetkisiz rota veya AJAX endpoint'ini çağırın.
            2. Herhangi bir yetkilendirme veya oturum doğrulaması olmadan veriler dönecektir.
            """)
            poc_http = textwrap.dedent(f"""
            POST {finding.rest_route if finding.rest_route else '/wp-admin/admin-ajax.php'} HTTP/1.1
            Host: target.local
            Content-Type: application/x-www-form-urlencoded
            Content-Length: [uzunluk]

            action=[ajax_action]
            """)
        else:
            poc_steps = "Bu zafiyet türü için manuel doğrulama ve exploit adımları uygulayın."
            poc_http  = "HTTP İsteği Şablonu Çıkarılamadı."

        return textwrap.dedent(f"""
        ======================================================================
        PROOF OF CONCEPT (PoC) EXPLOTATION GUIDE
        ======================================================================
        Target Plugin:  {slug}
        Vuln Type:      {finding.vuln_type} ({cwe})
        Severity:       {finding.severity}
        Line in Code:   {finding.line_no}
        Code Line:      {finding.line_content}

        EXPLOIT STEPS
        -------------
        {poc_steps.strip()}

        RAW HTTP REQUEST TEMPLATE
        -------------------------
        {poc_http.strip()}
        ======================================================================
        """).strip()

    def save_plugin_report(self, plugin: Dict, findings: List[Finding]) -> Optional[Path]:
        if not findings:
            return None
        slug = plugin.get("slug", "unknown")
        dir_ = self.output_dir / f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dir_.mkdir(parents=True, exist_ok=True)

        report_data = {
            "plugin": plugin,
            "total_findings": len(findings),
            "findings": []
        }
        for f in findings:
            cwe, cvss = CWE_MAP.get(f.vuln_type, ("CWE-Unknown", 5.0))
            report_data["findings"].append({
                "vuln_type": f.vuln_type,
                "cwe": cwe,
                "cvss": f.cvss_estimate,
                "file": f.file_path,
                "line": f.line_no,
                "code": f.line_content,
                "is_admin": f.is_admin_context
            })
            
            poc_content = self._generate_poc_template(slug, f)
            with open(dir_ / f"poc_{f.vuln_type.replace(' ', '_').lower()}_{f.line_no}.txt", "w", encoding="utf-8") as pf:
                pf.write(poc_content)

        with open(dir_ / "report.json", "w", encoding="utf-8") as jf:
            json.dump(report_data, jf, indent=4)
        return dir_


# ══════════════════════════════════════════════════════════════════════════════
#  LIVE DASHBOARD & ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

class WPCVEHunterOrchestrator:
    def __init__(self, config: Dict):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "WP-CVEHunter/3.1 Research Tool"})
        self.work_dir = OUTPUT_DIR / "temp"
        self.output_dir = OUTPUT_DIR / "reports"
        self.downloader = PluginDownloader(self.session, self.work_dir)
        self.discovery = PluginDiscovery(self.session, config["min_installs"], config["risk_threshold"])
        self.analyzer = PHPStaticAnalyzer()
        self.reporter = CVEReportGenerator(self.output_dir)
        self.cache_manager = ScanCacheManager(CACHE_FILE)

        self.scanned_count = 0
        self.skipped_count = 0
        self.vuln_count = 0
        self.current_plugin = "Hazırlanıyor..."
        self.recent_findings: List[str] = []
        self.lock = threading.Lock()

    def make_layout(self) -> Layout:
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", size=15),
            Layout(name="footer", size=3)
        )
        return layout

    def update_dashboard(self, layout: Layout):
        with self.lock:
            # UI değişkenlerinin kilit altındayken alınması Rich çakışmalarını önler
            scanned = self.scanned_count
            skipped = self.skipped_count
            vuln    = self.vuln_count
            cur_p   = self.current_plugin
            findings = list(self.recent_findings[-8:])

        layout["header"].update(Panel(
            f"[bold cyan]WP-CVEHunter v3.1[/bold cyan] | [dim]Taranan: {scanned} | Es Geçilen: {skipped} | Zafiyet: [bold red]{vuln}[/bold red][/dim]",
            border_style="cyan"
        ))
        findings_str = "\n".join(findings) if findings else "[dim]Henüz zafiyet bulunamadı...[/dim]"
        layout["main"].update(Panel(
            f"[yellow]O An Taranan:[/yellow] [bold white]{cur_p}[/bold white]\n\n"
            f"[bold red]Son Bulgular & PoC Taslakları (Gerçek Zamanlı):[/bold red]\n{findings_str}",
            title="🔍 Canlı Analiz Paneli", border_style="yellow"
        ))
        layout["footer"].update(Panel(
            "[dim]Çıkmak için CTRL+C tuşlarına basın. Raporlar 'wp_cve_hunter_output/reports' klasörüne yazılır.[/dim]",
            border_style="dim"
        ))

    def process_plugin(self, plugin: Dict):
        slug    = plugin.get("slug", "?")
        version = plugin.get("version", "")

        if self.cache_manager.is_scanned(slug, version):
            with self.lock:
                self.skipped_count += 1
            return

        with self.lock:
            self.current_plugin = f"{slug} v{version} (Risk: {plugin['_risk_score']})"

        plugin_dir = self.downloader.download_and_extract(plugin)
        if not plugin_dir:
            # İndirilemediyse de taranmış olarak işaretleyerek döngüye girmesini engelleriz
            self.cache_manager.mark_as_scanned(slug, version)
            return

        php_files = list(plugin_dir.rglob("*.php"))
        findings = []
        for pf in php_files:
            if "/vendor/" in str(pf) or "/node_modules/" in str(pf):
                continue
            findings.extend(self.analyzer.analyze_file(pf))

        # LOW Confidence olan şüpheli yalancı pozitifleri baştan ele
        valid_findings = [f for f in findings if f.confidence != Confidence.LOW]
        shutil.rmtree(plugin_dir, ignore_errors=True)

        self.cache_manager.mark_as_scanned(slug, version)

        with self.lock:
            self.scanned_count += 1
            if valid_findings:
                self.vuln_count += len(valid_findings)
                self.reporter.save_plugin_report(plugin, valid_findings)
                for vf in valid_findings:
                    self.recent_findings.append(
                        f"  [bold red]●[/bold red] [{vf.vuln_type}] {slug} -> {Path(vf.file_path).name}:{vf.line_no}"
                    )

    def run(self):
        console.clear()
        console.print(Panel(
            "[bold cyan]WP-CVEHunter v3.1 - Tarama Başlatılıyor[/bold cyan]\n"
            f"Filtre: {self.config['min_installs']}+ Kurulum | Risk Eşiği: {self.config['risk_threshold']}",
            border_style="cyan"
        ))
        
        candidates = list(self.discovery.stream_candidates())
        
        layout = self.make_layout()
        with Live(layout, refresh_per_second=4, screen=True) as live:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.process_plugin, c) for c in candidates]
                for future in as_completed(futures):
                    self.update_dashboard(layout)
                    if self.vuln_count > 0 and self.config.get("stop_on_first", True):
                        break
        
        console.clear()
        console.print(Panel(
            f"[bold green]Tarama Sonlandı![/bold green]\n\n"
            f"Taranan Plugin Sayısı: [bold]{self.scanned_count}[/bold]\n"
            f"Tekrar taranmayan: [bold cyan]{self.skipped_count}[/bold cyan]\n"
            f"Toplam Gerçek Zafiyet: [bold red]{self.vuln_count}[/bold red]\n"
            f"Tüm raporlar ve PoC kılavuzları [underline]wp_cve_hunter_output/reports[/underline] klasörüne kaydedilmiştir.",
            title="🎯 Sonuç Özet Raporu", border_style="green"
        ))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--min-installs", type=int, default=100)
    p.add_argument("--risk-threshold", type=int, default=40)
    args = p.parse_args()

    orchestrator = WPCVEHunterOrchestrator({
        "min_installs": args.min_installs,
        "risk_threshold": args.risk_threshold,
        "stop_on_first": False
    })
    try:
        orchestrator.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
