"""
Yapılandırma dosyası
Kendi bilgilerinizi buraya girin
"""

import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# GitHub AI Models API Ayarları
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "your_github_token_here")  # GitHub AI Models API token'ınız
GITHUB_API_BASE = "https://models.inference.ai.azure.com"  # GitHub AI Models endpoint
GITHUB_MODEL = os.getenv("GITHUB_MODEL", "gpt-4o")  # Kullanılacak model

# Telegram Ayarları
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_telegram_bot_token_here")  # @BotFather'dan aldığınız token
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "your_chat_id_here")  # Sizin chat ID'niz

# Tarama Ayarları
PLUGINS_PER_SCAN = 5  # Her taramada kaç plugin analiz edilecek (RAM'e göre ayarlayın)
WORK_DIR = "./work"  # Geçici çalışma dizini
RESULTS_DIR = "./results"  # Sonuçların kaydedileceği dizin
SCANNED_PLUGINS_DB = "./scanned_plugins.json"  # Taranan pluginlerin veritabanı

# WordPress API
WORDPRESS_API = "https://api.wordpress.org/plugins/info/1.2/"

# Filtreleme Kriterleri (ZAFİYET ARAMA STRATEJİSİ)
FILTER_CRITERIA = {
    # Az popüler pluginler (daha az incelenmiş olabilir)
    "max_active_installs": 100000,
    "min_active_installs": 50,
    
    # Eski pluginler (güncellenmeyen = zafiyet riski yüksek)
    "min_months_since_update": 2,
    "max_months_since_update": 60,
    
    "min_rating": 20,
    
    # Daha önce zafiyet bulunan kategoriler (öncelik ver)
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

# Taranan pluginleri takip et
TRACK_SCANNED_PLUGINS = True

# Analiz edilecek zafiyet türleri
VULNERABILITY_PATTERNS = {
    "SQL Injection": [
        r"\$wpdb->query\s*\(\s*[\"'].*\$",
        r"\$wpdb->get_results\s*\(\s*[\"'].*\$",
        r"mysql_query\s*\(",
        r"mysqli_query\s*\(",
        r"execute\s*\(\s*[\"'].*\$",
    ],
    "XSS (Cross-Site Scripting)": [
        r"echo\s+\$_(GET|POST|REQUEST)",
        r"print\s+\$_(GET|POST|REQUEST)",
        r"<\?=\s*\$_(GET|POST|REQUEST)",
        r"innerHTML\s*=.*\$_(GET|POST|REQUEST)",
    ],
    "CSRF": [
        r"wp_nonce",
        r"check_admin_referer",
    ],
    "File Upload": [
        r"move_uploaded_file",
        r"\$_FILES",
        r"wp_handle_upload",
    ],
    "Path Traversal": [
        r"file_get_contents\s*\(\s*\$",
        r"include\s*\(\s*\$",
        r"require\s*\(\s*\$",
        r"fopen\s*\(\s*\$",
    ],
    "Remote Code Execution": [
        r"eval\s*\(",
        r"system\s*\(",
        r"exec\s*\(",
        r"shell_exec\s*\(",
        r"passthru\s*\(",
    ],
    "Deserialization": [
        r"unserialize\s*\(\s*\$",
        r"maybe_unserialize\s*\(\s*\$",
    ],
}

# AI Analiz Prompts (Katı ve Gerçekçi Sızma Testi Kuralları)
ANALYSIS_PROMPT = """Sen dünyaca ünlü, halüsinasyon görmeyen, acımasız bir WordPress Güvenlik Araştırmacısısın (Senior Exploit Developer).

GÖREV: Aşağıdaki PHP kodunda SADECE VE SADECE GERÇEK, DIŞARIDAN İSTİSMAR EDİLEBİLİR (REAL WORLD EXPLOITABLE) zafiyetleri tespit et.

🔴 NELER ZAFİYET DEĞİLDİR? (BUNLARI KESİNLİKLE ATLA - VULNERABLE: FALSE VER):
1. Eklenti silme (`uninstall.php`), veritabanı tablosu temizleme (`DROP TABLE`, `DELETE FROM`) kodları ZAFİYET DEĞİLDİR.
2. Sadece Yönetici (Administrator/is_admin) yetkisindeki rutin admin işlemleri ZAFİYET DEĞİLDİR.
3. Dışarıdan kullanıcı girdisi ($_GET, $_POST, $_REQUEST, $_COOKIE, php://input) İÇERMEYEN kodlar ZAFİYET DEĞİLDİR.
4. $wpdb->prepare(), esc_sql(), intval(), (int), sanitize_text_field(), esc_html(), esc_attr() veya wp_verify_nonce() ile korunan kodlar ZAFİYET DEĞİLDİR.
5. Sabit stringler veya sadece fonksiyon tanımları ZAFİYET DEĞİLDİR.

🟢 GERÇEK ZAFİYET NEDİR? (SADECE BUNLARI RAPORLA):
1. Unauthenticated (Giriş yapmamış) veya Low-Privilege (Abone/Subscriber) kullanıcının dışarıdan göndereceği girdiyle SQL sorgusunu değiştirebilmesi (SQL Injection).
2. Dışarıdan gelen girdinin süzülmeden ekrana basılması ve başka kullanıcının oturumunu çalabilmesi (Reflected / Stored XSS).
3. Yetkisiz kullanıcının kritik admin fonksiyonlarını tetikleyebilmesi (Broken Access Control / Missing Nonce Check / Unauthenticated AJAX).
4. Dışarıdan dosya yükleyip PHP kodu çalıştırabilmesi (Arbitrary File Upload / RCE).
5. Dışarıdan gönderilen yol parametresiyle sistem dosyalarının okunabilmesi (Path Traversal / LFI).

Şüphen varsa veya %100 emin değilsen "vulnerable: false" yanıtı ver. Şişirme veya uydurma rapor KABUL EDİLEMEZ.

Kod:
{code}

Yanıtlama formatı (SADECE GEÇERLİ JSON):
{{
    "vulnerable": true/false,
    "vulnerabilities": [
        {{
            "type": "Zafiyet Türü (Örn: Unauthenticated SQL Injection)",
            "severity": "Critical/High",
            "cvss_score": 7.5-10.0,
            "location": "dosya:satır",
            "vulnerable_code": "Zafiyete sebep olan tam PHP kod satırı",
            "description": "Zafiyetin GERÇEK VE TEKNİK açıklaması",
            "exploit_scenario": "Saldırganın dışarıdan göndereceği istek ve parametreler",
            "poc_command": "Gerçek cURL testi örneği (Örn: curl -X POST ...)",
            "recommendation": "Geliştirici için kesin yama önerisi"
        }}
    ]
}}"""
