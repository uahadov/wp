"""
Yapılandırma dosyası
Wordfence Bug Bounty Standartlarına Göre Zafiyet Arama Motoru
"""

import os
from dotenv import load_dotenv

# .env dosyasını yükle (override=True ile sistem env değişkenlerini de geçersiz kılar)
load_dotenv(override=True)

# GitHub AI Models API (Yedek / Fallback)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_github_token_here")
GITHUB_API_BASE = "https://models.inference.ai.azure.com"
GITHUB_MODEL = os.getenv("GITHUB_MODEL", "gpt-4o")

# Google Gemini API (Birincil AI - 1500 istek/gün ücretsiz!)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# NVD (National Vulnerability Database) - Bilinen CVE eşleştirme için
# Ücretsiz kullanımda rate limit vardır; NVD_API_KEY ile aşılır.
NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_API_KEY = os.getenv("NVD_API_KEY", "")

# Tarama sırasında bilinen CVE kontrolü yapılsın mı?
# Not: her plugin için NVD isteği yapar; rate limit'e takılmamak için
# NVD_API_KEY tanımlamanız önerilir.
ENABLE_KNOWN_CVE_CHECK = os.getenv("ENABLE_KNOWN_CVE_CHECK", "false").lower() in ("true", "1", "yes")

# ---------------------------------------------------------------
# AI Sağlayıcı Seçimi (Kök düzeltme)
# PRIMARY   → Ana analiz (derin kod analizi, /m bot sorgusu)
# SECONDARY → Doğrulayıcı / Hakem (validator, /m2 bot sorgusu)
#
# Seçim kuralı: Google Gemini anahtar geçerliyse Gemini PRIMARY olur,
# aksi halde GitHub Models (GPT-4o) birincildir. Diğer sağlayıcı
# geçerli bir anahtara sahipse SECONDARY (doğrulayıcı) olur; yoksa
# SECONDARY boş kalır (tek sağlayıcı mod → yerel filtreler kullanılır).
# ---------------------------------------------------------------

_placeholder_keys = ("", "your_github_token_here", "your_gemini_api_key_here")
_github_ready = bool(GITHUB_TOKEN and GITHUB_TOKEN not in _placeholder_keys)
_gemini_ready = bool(GEMINI_API_KEY and GEMINI_API_KEY not in _placeholder_keys)


def _secondary_of(primary_is_gemini: bool):
    """Birincil sağlayıcının tersi olan, geçerli sağlayıcıyı döndürür."""
    if primary_is_gemini:
        return (_github_ready, GITHUB_API_BASE, GITHUB_TOKEN, GITHUB_MODEL, "GitHub Models (GPT-4o)")
    return (_gemini_ready, GEMINI_API_BASE, GEMINI_API_KEY, GEMINI_MODEL, "Google Gemini")


if _gemini_ready:
    PRIMARY_API_BASE = GEMINI_API_BASE
    PRIMARY_API_KEY = GEMINI_API_KEY
    PRIMARY_MODEL = GEMINI_MODEL
    PRIMARY_PROVIDER = "Google Gemini"
else:
    PRIMARY_API_BASE = GITHUB_API_BASE
    PRIMARY_API_KEY = GITHUB_TOKEN
    PRIMARY_MODEL = GITHUB_MODEL
    PRIMARY_PROVIDER = "GitHub Models (GPT-4o)"

_secondary = _secondary_of(primary_is_gemini=_gemini_ready)
SECONDARY_API_BASE = _secondary[1] if _secondary[0] else None
SECONDARY_API_KEY = _secondary[2] if _secondary[0] else None
SECONDARY_MODEL = _secondary[3] if _secondary[0] else None
SECONDARY_PROVIDER = _secondary[4] if _secondary[0] else None

# Telegram Ayarları
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_telegram_bot_token_here")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your_chat_id_here")

# Tarama Ayarları
PLUGINS_PER_SCAN = int(os.getenv("PLUGINS_PER_SCAN", "15"))  # 5 → 15'e çıkarıldı (3x hız)
WORK_DIR = os.getenv("WORK_DIR", "./work")
RESULTS_DIR = os.getenv("RESULTS_DIR", "./results")
SCANNED_PLUGINS_DB = os.getenv("SCANNED_PLUGINS_DB", "./scanned_plugins.json")

# Paralel Tarama Ayarları (v4.1 - YENİ)
ENABLE_PARALLEL_SCAN = os.getenv("ENABLE_PARALLEL_SCAN", "true").lower() in ("true", "1", "yes")
MAX_PARALLEL_WORKERS = int(os.getenv("MAX_PARALLEL_WORKERS", "3"))  # 1.5GB RAM için optimal: 3
CONCURRENT_DOWNLOADS = int(os.getenv("CONCURRENT_DOWNLOADS", "3"))  # Paralel plugin indirme

# False Positive Learning (v4.1 - YENİ)
ENABLE_FP_LEARNING = os.getenv("ENABLE_FP_LEARNING", "true").lower() in ("true", "1", "yes")
FP_PATTERNS_FILE = os.getenv("FP_PATTERNS_FILE", "fp_patterns.json")

# WordPress API
WORDPRESS_API = "https://api.wordpress.org/plugins/info/1.2/"

# Filtreleme Kriterleri (ZAFİYET ARAMA STRATEJİSİ)
FILTER_CRITERIA = {
    "max_active_installs": 100000,
    "min_active_installs": 50,
    "min_months_since_update": 2,
    "max_months_since_update": 60,
    "min_rating": 20,
    "prioritize_categories": [
        "security",
        "admin",
        "login",
        "file-upload",
        "forms",
        "ecommerce",
        "payment",
        "membership"
    ]
}

TRACK_SCANNED_PLUGINS = True

# Taint Analysis Ayarları (TRUE POSITIVE motoru)
# Bu, regex pattern matching yerine gerçek data-flow analizi yapar
ENABLE_TAINT_ANALYSIS = os.getenv("ENABLE_TAINT_ANALYSIS", "true").lower() in ("true", "1", "yes")

# Güvenlik limiti: Maksimum batch sayısı (sonsuz döngü koruması)
MAX_BATCHES = int(os.getenv("MAX_BATCHES", "20"))

# PoC Doğrulama (Docker ile gerçek exploit testi)
ENABLE_POC_VERIFICATION = os.getenv("ENABLE_POC_VERIFICATION", "false").lower() in ("true", "1", "yes")
DOCKER_WP_URL = os.getenv("DOCKER_WP_URL", "http://localhost:8080")

# WORDFENCE BUG BOUNTY PATTERNS (Hızlı Ön Tarama)
# NOT: Bu pattern'lar şüpheli dosyaları belirlemek içindir; gerçek zafiyet tespiti AI yapar.
VULNERABILITY_PATTERNS = {
    "SQL Injection": [
        r"\$wpdb->query\s*\(",
        r"\$wpdb->get_results\s*\(",
        r"\$wpdb->get_row\s*\(",
        r"\$wpdb->get_var\s*\(",
        # Doğrudan string birleştirme ile sorgu (daha riskli)
        r"\$wpdb->query\s*\(\s*[\"']SELECT",
    ],
    "Authentication Bypass / Account Takeover": [
        r"wp_set_current_user\s*\(",
        r"wp_set_auth_cookie\s*\(",
        r"wp_signon\s*\(",
        r"is_user_logged_in\s*\(\s*\)\s*\)",  # Yanlış nonce/auth atlaması
    ],
    "Broken Access Control / Missing Authorization": [
        r"add_action\s*\(\s*['\"]wp_ajax_nopriv_",
        r"add_action\s*\(\s*['\"]admin_post_nopriv_",
        r"update_option\s*\(",
        r"register_rest_route\s*\(",       # REST API endpoint'leri (permission_callback kontrolü gerekir)
        r"add_rewrite_rule\s*\(",
    ],
    "Arbitrary File Upload / RCE": [
        r"move_uploaded_file\s*\(",
        r"wp_handle_upload\s*\(",
        r"eval\s*\(",
        r"system\s*\(",
        r"exec\s*\(",
        r"passthru\s*\(",
        r"shell_exec\s*\(",
        r"popen\s*\(",
        r"proc_open\s*\(",
        r"assert\s*\(\s*\$",              # assert ile kod çalıştırma
    ],
    "Cross-Site Scripting (XSS)": [
        r"echo\s+\$_(GET|POST|REQUEST)",
        r"print\s+\$_(GET|POST|REQUEST)",
        r"<\?=\s*\$_(GET|POST|REQUEST)",
        r"echo\s+.*\$_(GET|POST|REQUEST)",  # Dolaylı echo
        r"_e\s*\(\s*\$_(GET|POST|REQUEST)",  # WP translation ile XSS
    ],
    "File System Access (LFI/LFD/File Delete)": [
        r"file_get_contents\s*\(\s*\$",
        r"file_put_contents\s*\(\s*\$",
        r"unlink\s*\(\s*\$",
        r"wp_delete_file\s*\(",
        r"include\s*\(\s*\$",
        r"require\s*\(\s*\$",
        r"include_once\s*\(\s*\$",
        r"require_once\s*\(\s*\$",
        r"readfile\s*\(\s*\$",
    ],
    "SSRF / Open Redirect": [
        r"wp_remote_get\s*\(\s*\$",
        r"wp_remote_post\s*\(\s*\$",
        r"curl_exec\s*\(",
        r"wp_redirect\s*\(\s*\$",
        r"wp_safe_redirect\s*\(\s*\$_(GET|POST|REQUEST)",
    ],
    "PHP Object Injection": [
        r"unserialize\s*\(\s*\$",
        r"unserialize\s*\(\s*base64_decode",
        r"maybe_unserialize\s*\(\s*\$",
    ],
    "CSRF (Missing Nonce)": [
        r"wp_ajax_nopriv_.*\n.*\$_(POST|GET|REQUEST)",  # nopriv action + user input, nonce yok
        r"admin_post_nopriv_.*\n.*\$_(POST|GET|REQUEST)",
    ]
}

# TAINT FLOW DOĞRULAMA PROMPT (ULTRA STRICT - v4.0)
ANALYSIS_PROMPT = """Sen Wordfence ve Patchstack standartlarında çalışan Kıdemli Güvenlik Araştırmacısısın.

⚠️ ULTRA STRICT MODE: FALSE POSITIVE TOLERANCE = 0%

SANA VERİLEN: Taint analysis motoru tarafından TESPİT EDİLMİŞ veri akışı (source -> sink).
GÖREVİN: Bu akışı inceleyip GERÇEKten CVE değeri olan istismar edilebilir zafiyet OLUP OLMADIĞINI doğrula.

🚨 ÖNEMLİ KURALLAR:
1. Sana zaten bir taint akışı verildi. SENİN GÖREVİN KODDAN YENİ ZAFİYET BULMAK DEĞİL.
2. Verilen taint akışını DOĞRULA veya REDDET. SADECE verilen akışla ilgili karar ver.
3. ŞÜPHELİ ise → REDDET (vulnerable: false)
4. %100 EMIN değilsen → REDDET
5. PoC yazamıyorsan → REDDET

=== TAINT ANALİZİ SONUCU (DOĞRULANACAK AKIŞ) ===
{taint_info}
=== TAINT ANALİZİ SONU ===

=== İLGİLİ PHP KOD ===
{code}
=== KOD SONU ===

🔍 ULTRA STRICT DOĞRULAMA KRİTERLERİ:

✅ KABUL ET (vulnerable: true) SADECE EĞER:
1. ✓ Source: DIŞARIDAN gelen kullanıcı girdisi ($_GET, $_POST, $_REQUEST, $_COOKIE, php://input, REST API)
2. ✓ Sink: GERÇEKTEN tehlikeli ($wpdb->query, eval, system, include, unlink, unserialize, vb.)
3. ✓ NO SANITIZER: Source ve sink arasında HİÇBİR sanitizer YOK
   - SQL için: $wpdb->prepare() YOK VE intval()/absint()/(int) YOK
   - XSS için: esc_html()/esc_attr() YOK
   - File için: sanitize_file_name() YOK
   - Genel: sanitize_text_field() YOK
4. ✓ NO AUTH CHECK: wp_verify_nonce() YOK VE check_ajax_referer() YOK
5. ✓ NO CAPABILITY: current_user_can() YOK VE is_admin() YOK (veya bypass edilebilir)
6. ✓ UNAUTHENTICATED: Dışarıdan, giriş yapmadan istismar edilebilir
7. ✓ IMPACT: Gerçek zarar var (data loss, RCE, XSS, SQL injection, vb.)
8. ✓ CVSS >= 7.0: Orta-Yüksek-Kritik seviye
9. ✓ PoC: Gerçekçi curl komutu yazabilirsin
10. ✓ NOT NORMAL BEHAVIOR: WooCommerce "add to cart", admin-only işlem değil

❌ REDDET (vulnerable: false) EĞER:
1. ✗ Sanitizer VAR (intval, prepare, esc_html, sanitize_*, vb.)
2. ✗ Nonce check VAR (wp_verify_nonce, check_ajax_referer)
3. ✗ Admin-only (is_admin() && no bypass)
4. ✗ WooCommerce normal müşteri işlemi (add_to_cart, product_id)
5. ✗ uninstall.php (not a vulnerability)
6. ✗ Source ve sink arasında bağlantı YOK
7. ✗ False positive riski VAR
8. ✗ PoC yazamıyorsun (gerçekçi değil)
9. ✗ CVSS < 7.0 (düşük etki)
10. ✗ ŞÜPHELİ (emin değilsen REDDET)

💡 POC KOMUTU KURALLARI:
- Gerçek WordPress endpoint kullan (admin-ajax.php, wp-json/wp/v2/, vb.)
- Gerçek parametre isimleri kullan (action=, id=, vb.)
- cURL formatında yaz
- Çalışabilir olmalı (test edilebilir)
- ÖRNEK: curl -X POST 'https://target.com/wp-admin/admin-ajax.php' --data 'action=vulnerable_action&id=1 OR 1=1'

🎯 KARAR VER:
- Eğer TÜM ✅ kriterler karşılanıyor ise → vulnerable: true
- Eğer HERHANGI BİR ❌ kriter varsa → vulnerable: false
- ŞÜPHELİ ise → vulnerable: false

⚠️ HATIRLA: FALSE POSITIVE = SİSTEMİN GÜVEN KAYBI. ŞÜPHELİ ise REDDET!

Yanıtlama formatı (SADECE GEÇERLİ JSON, MARKDOWN YOK):
{{
    "vulnerable": true,
    "vulnerabilities": [
        {{
            "type": "Zafiyet türü (SQL Injection, RCE, XSS, LFI, File Upload, Deserialization, SSRF)",
            "wordfence_category": "Injection / File System Access / Authentication / Deserialization / SSRF",
            "severity": "Critical/High/Medium (7.0+ only)",
            "cvss_score": 7.0-10.0,
            "location": "dosya.php:satır_numarası",
            "vulnerable_code": "Zafiyete sebep olan tam PHP kod satırı (source → sink akışı)",
            "source": "Kullanıcı girdisi kaynağı (Örn: $_POST['id'])",
            "sink": "Tehlikeli fonksiyon (Örn: $wpdb->query())",
            "description": "ULTRA NET teknik açıklama: source'dan sink'e nasıl ulaşıyor, NEDEN sanitizer yok",
            "exploit_scenario": "Adım adım GERÇEK istismar senaryosu: 1. Attacker gönderir... 2. Kod çalıştırır... 3. Sonuç...",
            "poc_command": "curl -X POST 'https://target.com/wp-admin/admin-ajax.php' --data 'action=xxx&param=PAYLOAD' (GERÇEK, ÇALIŞIR KOMUT)",
            "recommendation": "Yama önerisi: $wpdb->prepare() kullan / intval() ekle / esc_html() kullan / vb."
        }}
    ]
}}

veya EĞER REDDET ise:
{{
    "vulnerable": false,
    "vulnerabilities": []
}}
"""