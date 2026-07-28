# 🎯 CVE Bulma Stratejileri

## Neden Bu Strateji İşe Yarar?

### İstatistikler:
- WordPress eklentileri: **60,000+**
- Aktif güvenlik araştırmacıları: ~1,000
- Her araştırmacı: Genelde popüler pluginlere bakar

**Sonuç:** 50,000+ az bilinen plugin **hiç incelenmemiş!**

---

## 🎲 Başarı Olasılığı

### Popüler Pluginler (Eski Yöntem)
```
WooCommerce, Yoast SEO, Contact Form 7...
→ 10,000+ araştırmacı bakıyor
→ Dakikalar içinde yamalar
→ Başarı şansı: %0.1
```

### Az Bilinen + Eski Pluginler (Yeni Yöntem)
```
2-3 yıl güncellenmemiş
1,000-10,000 kurulum arası
→ Belki hiç kimse bakmamış
→ Başarı şansı: %10-20
```

---

## 🔍 Hedef Seçimi Stratejileri

### Strateji 1: "Zombi Pluginler" ⭐⭐⭐⭐⭐
**En Etkili Yöntem**

```python
# config.py ayarları
FILTER_CRITERIA = {
    "max_active_installs": 30000,
    "min_active_installs": 500,
    "min_months_since_update": 18,  # 1.5 yıl
    "max_months_since_update": 36,  # 3 yıl
}
```

**Mantık:**
- Plugin terk edilmiş ama hala kullanılıyor
- Geliştirici artık bakmıyor
- Güvenlik yamaları yok
- **CVE bulma şansı: ÇOK YÜKSEK**

**Örnek Hedefler:**
- Eski tema yönetim pluginleri
- Terk edilmiş SEO araçları
- Kullanılmayan form builders

---

### Strateji 2: "Güvenlik İronisi" ⭐⭐⭐⭐
**İronik ama Gerçek**

```python
FILTER_CRITERIA = {
    "prioritize_categories": [
        "security",
        "firewall", 
        "anti-spam",
        "backup"
    ],
    "min_months_since_update": 6,
}
```

**Mantık:**
- Güvenlik pluginleri kendileri güvensiz olabilir
- Yüksek kompleksite = daha fazla hata
- Herkes "güvenlik plugini güvenlidir" sanır
- **İronik ama sık görülür!**

**Gerçek Örnekler:**
- Wordfence eski versiyonları (CVE-2021-XXXX)
- iThemes Security (CVE-2020-XXXX)

---

### Strateji 3: "Dosya Yükleme Avcısı" ⭐⭐⭐⭐⭐
**Kritik Zafiyetler**

```python
FILTER_CRITERIA = {
    "prioritize_categories": [
        "file-upload",
        "media",
        "gallery"
    ],
    "max_active_installs": 20000,
}
```

**Mantık:**
- Dosya yükleme = en kritik zafiyet noktası
- Bir hata = RCE (Remote Code Execution)
- **CVSS Score: 9.0-10.0 (Critical)**

**Aranacak Zafiyetler:**
- File type bypass (.php.jpg)
- Path traversal (../../shell.php)
- MIME type validation eksikliği

---

### Strateji 4: "E-Ticaret Altını" ⭐⭐⭐⭐
**Yüksek Değerli Hedefler**

```python
FILTER_CRITERIA = {
    "prioritize_categories": [
        "payment",
        "ecommerce",
        "woocommerce"
    ],
    "min_active_installs": 1000,  # Gerçekten kullanılan
    "max_active_installs": 15000,
}
```

**Mantık:**
- Ödeme sistemleri = yüksek değer
- Küçük eklentiler = az test edilmiş
- **Bug bounty programları var** (ekstra para!)

**Aranacak Zafiyetler:**
- SQL Injection (ödeme datası çalma)
- CSRF (sahte ödemeler)
- XSS (kredi kartı çalma)

---

### Strateji 5: "Admin Panel Avcısı" ⭐⭐⭐⭐
**Privilege Escalation**

```python
FILTER_CRITERIA = {
    "prioritize_categories": [
        "admin",
        "dashboard",
        "user-management"
    ],
    "min_months_since_update": 12,
}
```

**Mantık:**
- Admin paneli = tam kontrol
- Privilege escalation = yüksek CVSS
- **Bir zafiyet = tüm siteye erişim**

---

### Strateji 6: "Form Hunter" ⭐⭐⭐
**SQL Injection Cenneti**

```python
FILTER_CRITERIA = {
    "prioritize_categories": [
        "forms",
        "contact",
        "survey"
    ],
    "max_active_installs": 10000,
}
```

**Mantık:**
- Form = kullanıcı input
- Input = zafiyet potansiyeli
- SQL Injection, XSS çok yaygın

---

## 📅 Zaman Bazlı Hedefleme

### Yeni Çıkan Eski Versiyon
```python
# Bugün: 2026-07-29
# Hedef: Tam 6 ay-1 yıl önce güncellenen

FILTER_CRITERIA = {
    "min_months_since_update": 6,
    "max_months_since_update": 12,
}
```

**Mantık:**
- Çok yeni değil (zaten incelenmiş)
- Çok eski değil (hala kullanılıyor)
- **Sweet spot: 6-12 ay**

---

## 🎯 Günlük Tarama Planı

### Hafta İçi Planı

**Pazartesi:** Zombi Pluginler
```bash
# config.py → min_months_since_update = 18
python3 scanner.py
```

**Salı:** Güvenlik Pluginleri
```bash
# config.py → prioritize_categories = ["security"]
python3 scanner.py
```

**Çarşamba:** Dosya Yükleme
```bash
# config.py → prioritize_categories = ["file-upload"]
python3 scanner.py
```

**Perşembe:** E-Ticaret
```bash
# config.py → prioritize_categories = ["payment", "ecommerce"]
python3 scanner.py
```

**Cuma:** Admin Panelleri
```bash
# config.py → prioritize_categories = ["admin"]
python3 scanner.py
```

**Hafta Sonu:** Rastgele tarama
```bash
# Varsayılan ayarlar
python3 scanner.py
```

---

## 🔬 Manuel Doğrulama Adımları

AI zafiyet buldu? **Kendin doğrula!**

### 1. Local WordPress Kurulumu
```bash
# Docker ile hızlı test
docker run -d -p 8080:80 wordpress

# Plugin'i kur
# Zafiyeti test et
```

### 2. Exploit Geliştir
```python
# Örnek: SQL Injection
import requests

url = "http://localhost:8080/wp-admin/admin-ajax.php"
payload = {"action": "vulnerable_action", "id": "1' OR '1'='1"}

response = requests.post(url, data=payload)
print(response.text)
```

### 3. Impact Ölç
```
Low: Sadece bilgi sızıntısı
Medium: Authenticated kullanıcı gerekli
High: Unauthenticated erişim
Critical: RCE veya tam site ele geçirme
```

---

## 📝 CVE Başvuru Hazırlığı

Zafiyet doğrulandı? **CVE başvurusunu hazırla:**

### Gerekli Bilgiler:
```
1. Plugin Adı ve Versiyonu
   → "Contact Form Builder v2.3.4"

2. Zafiyet Türü
   → "SQL Injection"

3. Etkilenen Kod
   → "admin-ajax.php satır 234"

4. CVSS Score
   → "8.5 (High)"

5. Exploit Senaryosu
   → "Unauthenticated attacker can..."

6. PoC (Proof of Concept)
   → curl komutu veya Python script

7. Çözüm Önerisi
   → "Prepared statements kullan"

8. Timeline
   → "2026-07-29: Bulundu"
   → "2026-08-01: Geliştiriciye bildirildi"
   → "2026-10-29: 90 gün sonra public"
```

---

## 🏆 Başarı Metrikleri

### Haftalık Hedefler:
```
Pazartesi-Pazar:
- 35 plugin tara (her gün 5)
- 2-5 potansiyel zafiyet bul
- 1 zafiyeti manuel doğrula
```

### Aylık Hedefler:
```
- 150 plugin tara
- 10+ potansiyel zafiyet
- 2-3 doğrulanmış zafiyet
- 1 CVE başvurusu
```

### Yıllık Hedef:
```
🎯 5-10 CVE Al!
```

---

## 💡 Pro İpuçları

### 1. Combo Zafiyetler
Bir zafiyet başka bir zafiyetle birleşebilir:
```
XSS + CSRF = Tam hesap ele geçirme
SQL Injection + File Write = RCE
```

### 2. Version Range
Eski versiyonları da kontrol et:
```bash
# WordPress.org'dan eski versiyonları indir
wget https://downloads.wordpress.org/plugin/plugin-name.1.0.0.zip
```

### 3. Benzer Pluginler
Bir zafiyet buldun? **Benzer pluginlerde de ara:**
```
"Contact Form A" SQL Injection var
→ "Contact Form B" de var mı bak
```

### 4. Developer Takibi
Bir geliştirici kötü kod yazıyorsa:
```
→ Aynı geliştiricinin diğer pluginlerine bak
→ Muhtemelen aynı hatayı yapmıştır
```

### 5. GitHub Issues
Plugin GitHub'daysa:
```bash
# Issues'ları tara
gh issue list --repo user/plugin --state all
# "security" "vulnerability" ara
```

---

## ⚠️ Etik Kurallar

### YAPILMASI GEREKENLER ✅
- Bulduğun zafiyeti geliştiriciye özel bildir
- 90 gün süre tanı (responsible disclosure)
- Test ortamında çalış (production'a dokunma)
- CVE başvurusunda dürüst ol

### YAPILMAMASI GEREKENLER ❌
- Başkalarının sitelerini izinsiz test etme
- Zafiyeti hemen public yapma
- Exploit'i kötü amaçlı paylaşma
- Şantaj/para isteme

---

## 🚀 Hızlı Başlangıç

```bash
# 1. En etkili stratejiyi seç (Zombi Pluginler)
nano config.py
# min_months_since_update = 18

# 2. İlk taramayı çalıştır
python3 scanner.py

# 3. Telegram'dan bildirimleri bekle
# 4. Bulguları manuel doğrula
# 5. CVE başvurusunu hazırla
# 6. Zengin ol! (şaka)
```

---

## 📚 Daha Fazla Kaynak

- CVE Başvurusu: https://cveform.mitre.org/
- WordPress Security: https://developer.wordpress.org/plugins/security/
- CVSS Calculator: https://www.first.org/cvss/calculator/3.1
- Bug Bounty: https://hackerone.com/

---

**İyi avlar! 🎯 İlk CVE'niz bu stratejilerle gelecek!** 🏆
