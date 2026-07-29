"""
Yapılandırma dosyası
Kendi bilgilerinizi buraya girin
"""

# GitHub AI Models API Ayarları
GITHUB_TOKEN = "your_github_token_here"  # GitHub AI Models API token'ınız
GITHUB_API_BASE = "https://models.inference.ai.azure.com"  # GitHub AI Models endpoint
GITHUB_MODEL = "gpt-4o"  # Kullanılacak model

# Telegram Ayarları
TELEGRAM_BOT_TOKEN = "your_telegram_bot_token_here"  # @BotFather'dan aldığınız token
TELEGRAM_CHAT_ID = "6532122431"  # Sizin chat ID'niz

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
    "max_active_installs": 100000,  # 50K → 100K (daha geniş)
    "min_active_installs": 50,      # 100 → 50 (daha düşük)
    
    # Eski pluginler (güncellenmeyen = zafiyet riski yüksek)
    "min_months_since_update": 2,   # 3 → 2 ay (daha yeni olanlar dahil)
    "max_months_since_update": 60,  # 48 → 60 ay (5 yıl, daha eski)
    
    # Rating filtresi (çok kötü ratingli olanları atla - zaten kullanılmıyor)
    "min_rating": 20,  # 50 → 20 (çok daha geniş)
    
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

# Taranan pluginleri takip et (aynı plugini tekrar taramayı önle)
TRACK_SCANNED_PLUGINS = True  # False yaparsanız her seferinde tüm pluginleri tarar

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

# AI Analiz Prompts
ANALYSIS_PROMPT = """Sen bir siber güvenlik uzmanısın. WordPress plugin kodunu analiz ediyorsun.

Aşağıdaki kod parçasını incele ve güvenlik zafiyetlerini tespit et:

{code}

Lütfen şunları kontrol et:
1. SQL Injection zafiyetleri
2. XSS (Cross-Site Scripting) zafiyetleri
3. CSRF koruması eksiklikleri
4. Dosya yükleme güvenlik açıkları
5. Path Traversal zafiyetleri
6. Remote Code Execution riskleri
7. Güvensiz deserialization

Eğer bir zafiyet bulursan:
- Zafiyet türünü belirt
- Hangi satırda olduğunu söyle
- Güvenlik riskini açıkla
- Exploit senaryosu ver
- CVSSv3 skorunu tahmin et

JSON formatında yanıt ver:
{
    "vulnerable": true/false,
    "vulnerabilities": [
        {
            "type": "zafiyet türü",
            "severity": "Critical/High/Medium/Low",
            "cvss_score": 0.0-10.0,
            "location": "dosya:satır",
            "description": "detaylı açıklama",
            "exploit_scenario": "nasıl istismar edilir",
            "recommendation": "nasıl düzeltilir"
        }
    ]
}

SADECE gerçek ve kesin zafiyetleri raporla. Tahmine dayalı veya belirsiz durumları ekleme."""
