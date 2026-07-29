"""
Yapılandırma dosyası
Wordfence Bug Bounty Standartlarına Göre Zafiyet Arama Motoru
"""

import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# GitHub AI Models API Ayarları
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_github_token_here")
GITHUB_API_BASE = "https://models.inference.ai.azure.com"
GITHUB_MODEL = os.getenv("GITHUB_MODEL", "gpt-4o")

# Telegram Ayarları
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_telegram_bot_token_here")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your_chat_id_here")

# Tarama Ayarları
PLUGINS_PER_SCAN = 5
WORK_DIR = "./work"
RESULTS_DIR = "./results"
SCANNED_PLUGINS_DB = "./scanned_plugins.json"

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

# WORDFENCE BUG BOUNTY PATTERNS (Hızlı Ön Tarama)
VULNERABILITY_PATTERNS = {
    "SQL Injection": [
        r"\$wpdb->query\s*\(",
        r"\$wpdb->get_results\s*\(",
        r"\$wpdb->get_row\s*\(",
        r"\$wpdb->get_var\s*\(",
    ],
    "Authentication Bypass / Account Takeover": [
        r"wp_set_current_user\s*\(",
        r"wp_set_auth_cookie\s*\(",
        r"wp_signon\s*\(",
    ],
    "Broken Access Control / Missing Authorization": [
        r"add_action\s*\(\s*['\"]wp_ajax_nopriv_",
        r"add_action\s*\(\s*['\"]admin_post_nopriv_",
        r"update_option\s*\(",
    ],
    "Arbitrary File Upload / RCE": [
        r"move_uploaded_file\s*\(",
        r"wp_handle_upload\s*\(",
        r"eval\s*\(",
        r"system\s*\(",
    ],
    "Cross-Site Scripting (XSS)": [
        r"echo\s+\$_(GET|POST|REQUEST)",
        r"print\s+\$_(GET|POST|REQUEST)",
        r"<\?=\s*\$_(GET|POST|REQUEST)",
    ],
    "File System Access (LFI/LFD/File Delete)": [
        r"file_get_contents\s*\(\s*\$",
        r"unlink\s*\(\s*\$",
        r"wp_delete_file\s*\(",
        r"include\s*\(\s*\$",
        r"require\s*\(\s*\$",
    ],
    "SSRF / Open Redirect": [
        r"wp_remote_get\s*\(\s*\$",
        r"wp_remote_post\s*\(\s*\$",
        r"curl_exec\s*\(",
        r"wp_redirect\s*\(\s*\$",
    ]
}

# WORDFENCE RESMİ ZAFIYET TAKSONOMİSİNE GÖRE AI KATI PROMPT
ANALYSIS_PROMPT = """Sen Wordfence ve Patchstack standartlarında çalışan Kıdemli Güvenlik Araştırmacısısın (Bug Bounty Hunter).

GÖREV: Aşağıdaki WordPress PHP kodunu analiz et ve SADECE WORDFENCE BUG BOUNTY kategorilerine uyan GERÇEK, DİŞARIDAN İSTİSMAR EDİLEBİLİR zafiyetleri bul.

🎯 KABUL EDİLEN WORDFENCE ZAFIYET KATEGORİLERİ:
1. Authentication & Authorization:
   - Account Takeover (Admin / User)
   - Authentication Bypass (Admin / Non-Admin)
   - Privilege Escalation (Admin / Non-Admin)
   - Insecure Direct Object Reference (IDOR)
   - Missing Authorization (AJAX / REST API / Admin Actions)

2. Injection & Code Execution:
   - SQL Injection (Full Access / Standard DB Read)
   - Remote Code Execution (RCE) / Code Injection
   - Local File Inclusion (LFI) / Remote File Inclusion (RFI)
   - PHP Object Injection (Deserialization)
   - Arbitrary Shortcode Execution

3. File System Access:
   - Arbitrary File Upload (Leading to RCE)
   - Arbitrary File Read / Download
   - Arbitrary File Deletion (Unlink)
   - Directory Traversal

4. Cross-Site Vulnerabilities & Content Manipulation:
   - Stored / Reflected Cross-Site Scripting (XSS)
   - CSRF (Availability / Confidentiality / Integrity Impact)
   - Arbitrary Option / Settings Change (Site Takeover)

5. Server & Network Abuse:
   - Server-Side Request Forgery (SSRF)
   - Open Redirect

⛔ KESİNLİKLE YASAK VE ZAFİYET SAYILMAYAN DURUMLAR (VULNERABLE: FALSE VER):
- 'uninstall.php' veya eklenti silme/kaldırma kodları ZAFİYET DEĞİLDİR.
- Sadece `is_admin()` veya `current_user_can('manage_options')` kontrolünden geçen yetkili yönetici fonksiyonları ZAFİYET DEĞİLDİR.
- Dışarıdan kullanıcı girdisi ($_GET, $_POST, $_REQUEST, $_COOKIE, php://input, REST API params) İÇERMEYEN sabit kodlar ZAFİYET DEĞİLDİR.
- $wpdb->prepare(), intval(), sanitize_text_field(), esc_html(), esc_attr(), wp_verify_nonce() ile tam korunan kodlar ZAFİYET DEĞİLDİR.
- Önemsiz bilgi ifşası (WordPress versiyonu vs.) ZAFİYET DEĞİLDİR.

Kod:
{code}

Yanıtlama formatı (SADECE GEÇERLİ JSON):
{{
    "vulnerable": true/false,
    "vulnerabilities": [
        {{
            "type": "Wordfence Zafiyet Kategorisi (Örn: Authentication Bypass (Admin))",
            "wordfence_category": "Authentication & Authorization / File System Access / Injection",
            "severity": "Critical/High/Medium",
            "cvss_score": 7.0-10.0,
            "location": "dosya:satır",
            "vulnerable_code": "Zafiyete sebep olan tam 1-3 satırlık PHP kodu",
            "description": "Wordfence standartlarına uygun net teknik açıklama",
            "exploit_scenario": "Dışarıdan gelen istek ve parametrelerle adım adım istismar senaryosu",
            "poc_command": "Gerçek cURL veya HTTP PoC isteği örneği",
            "recommendation": "Yama önerisi"
        }}
    ]
}}"""
