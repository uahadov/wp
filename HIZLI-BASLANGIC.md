# ⚡ Hızlı Başlangıç Kılavuzu

## 🚀 5 Dakikada Kurulum

### 1️⃣ Dosyaları Sunucuya Yükle

```bash
# Sunucuya SSH bağlan
ssh kullanici@sunucu-ip

# ZIP yüklediyseniz
unzip wordpress-vuln-scanner.zip
cd wordpress-vuln-scanner

# Git kullandıysanız
git clone <repo-url>
cd wordpress-vuln-scanner
```

### 2️⃣ Kurulumu Çalıştır

```bash
chmod +x setup.sh
./setup.sh
```

**Kurulum sırasında istenenler:**
- ✅ GitHub AI Models Token → https://github.com/marketplace/models
- ✅ Telegram Bot Token → @BotFather'dan alın
- ✅ Telegram Chat ID → Sizinki: `6532122431`

### 3️⃣ İlk Taramayı Başlat

```bash
# İnteraktif menü (önerilen)
chmod +x quick-start.sh
./quick-start.sh

# Veya direkt tarama
source venv/bin/activate
python3 scanner.py
```

---

## 📱 Telegram Bot Kurulumu

### Bot Oluştur:
1. Telegram'da **@BotFather** aç
2. `/newbot` yaz
3. İsim ver: "WP Vuln Scanner"
4. Username: "my_wp_scanner_bot"
5. Token'ı kopyala

### Chat ID'ni Bul:
- **Sizin Chat ID: 6532122431**
- Kurulumda enter'a bas, bu kullanılacak

---

## 🎯 Hangi Stratejiyi Seçmeliyim?

### Yeni Başlıyorsanız:
```
🧟 Zombi Pluginler
→ 1.5-3 yıl güncellenmemiş
→ En yüksek başarı oranı
→ quick-start.sh'da #1 seçin
```

### Kritik Zafiyetler İçin:
```
📎 Dosya Yükleme
→ RCE riski yüksek
→ CVSS 9.0-10.0
→ quick-start.sh'da #3 seçin
```

### Para Kazanmak İçin:
```
💳 E-Ticaret & Ödeme
→ Bug bounty var
→ Yüksek değer
→ quick-start.sh'da #4 seçin
```

---

## 📊 Nasıl Çalışır?

### Adım 1: Plugin Bulma
```
WordPress.org'dan 500 plugin alır
↓
Filtreleme yapar:
  • 100-50,000 arası kurulum
  • 3 ay - 4 yıl arası güncelleme
  • 50+ rating
↓
En riskli 5 plugin seçilir
```

### Adım 2: Analiz
```
Plugin indirilir (EN SON VERSİYON)
↓
PHP dosyaları taranır
↓
Pattern matching (SQL, XSS, RCE vb.)
↓
AI ile derin analiz (GitHub Models)
↓
False positive filtreleme
```

### Adım 3: Raporlama
```
Zafiyet bulundu mu?
↓
Evet → Telegram'a bildirim
↓
JSON rapor oluştur
↓
Veritabanına kaydet (tekrar tarama önle)
```

---

## 🔍 İlk Sonuçlarım Geldi, Ne Yapmalıyım?

### 1. Telegram Mesajını Kontrol Et
```
🚨 ZAFIYET BULUNDU!

Plugin: Some Plugin
Versiyon: 1.2.3
Zafiyet: SQL Injection
Önem: High (CVSS: 8.5)

→ Detayları oku
```

### 2. JSON Raporunu İncele
```bash
# En son raporu bul
ls -lt results/*.json | head -1

# İçeriği oku
cat results/plugin-name_20260729_143000.json | python3 -m json.tool
```

### 3. Manuel Doğrulama YAP!
```
AI %100 doğru olmayabilir!

✅ YAPILMASI GEREKENLER:
  1. Local WordPress kurulumu yap
  2. Plugin'i kur
  3. Zafiyeti test et
  4. Exploit yazarak doğrula
  5. Impact ölç (Low/Medium/High/Critical)
```

### 4. Responsible Disclosure
```
✉️  1. Geliştiriciye özel e-posta gönder
     • Zafiyeti açıkla
     • Exploit senaryosu ver
     • Çözüm öner
     • 90 gün süre tanı

⏰ 2. 90 gün bekle
     • Geliştirici düzeltsin
     • Güncelleme yayınlansın

📝 3. CVE başvurusu yap
     • https://cveform.mitre.org/
     • Tüm detayları ver
```

---

## ⚙️ Ayarları Değiştirme

### Daha Fazla Plugin Tara
```python
# config.py
PLUGINS_PER_SCAN = 10  # 5 → 10
```

### Daha Eski Pluginlere Odaklan
```python
# config.py
FILTER_CRITERIA = {
    "min_months_since_update": 24,  # 3 ay → 2 yıl
    "max_months_since_update": 60,  # 4 yıl → 5 yıl
}
```

### Sadece Belirli Kategoriler
```python
# config.py
FILTER_CRITERIA = {
    "prioritize_categories": [
        "file-upload",
        "security"
    ]
}
```

---

## 🤔 Sık Sorulan Sorular

### Kaç sürede CVE alırım?
```
Ortalama: 1-3 ay
→ Haftada 5 tarama yaparsanız
→ Ayda 20 tarama = 100 plugin
→ %10 başarı oranı = 10 potansiyel zafiyet
→ 1-2 gerçek zafiyet
→ 1 CVE başvurusu
```

### Hangi zafiyetler daha değerli?
```
💎 En Değerli:
  1. RCE (Remote Code Execution) - CVSS 9.0-10.0
  2. SQL Injection (Unauthenticated) - CVSS 8.0-9.0
  3. Authentication Bypass - CVSS 8.0-9.0

💰 Orta Değerli:
  4. XSS (Stored) - CVSS 6.0-8.0
  5. CSRF - CVSS 5.0-7.0
  6. File Upload - CVSS 7.0-9.0

📄 Düşük Değerli:
  7. XSS (Reflected) - CVSS 4.0-6.0
  8. Information Disclosure - CVSS 3.0-5.0
```

### RAM yetmiyor ne yapmalıyım?
```bash
# Swap artır
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Plugin sayısını azalt
# config.py → PLUGINS_PER_SCAN = 3
```

### Aynı pluginleri tekrar tarıyor
```bash
# Veritabanını kontrol et
cat scanned_plugins.json

# Veritabanını sıfırla (yeniden tara)
rm scanned_plugins.json

# Veya config.py'de kapat
# TRACK_SCANNED_PLUGINS = False
```

### API limiti aşıldı hatası
```python
# config.py
PLUGINS_PER_SCAN = 2  # Daha az plugin

# scanner.py'de bekleme süresini artır
time.sleep(5)  # 1 → 5 saniye
```

---

## 📈 İlerleme Takibi

### İstatistikleri Gör
```bash
./quick-start.sh
# Seçenek 9: İstatistikler

# Veya manuel:
python3 << EOF
import json
with open('scanned_plugins.json') as f:
    data = json.load(f)
total = len(data)
vulns = sum(1 for p in data.values() if p['found_vulnerabilities'])
print(f"Taranan: {total}, Zafiyet: {vulns}, Oran: {vulns/total*100:.1f}%")
EOF
```

### Logları İzle
```bash
# Cron ile çalışıyorsa
tail -f logs/scanner.log

# Real-time izleme
python3 scanner.py 2>&1 | tee logs/manual-run.log
```

---

## 🏆 Başarı Hikayeleri (Sizinki de eklenecek!)

```
🎯 Hedef: İlk CVE
📅 Süre: 1-3 ay
📊 Tarama: Haftada 5 (topla ~80 plugin/ay)
🎉 Sonuç: 2-5 CVE/yıl

💡 İpucu:
  • Sabırlı olun
  • Manuel doğrulama yapmayı unutmayın
  • Etik kurallara uyun
  • Community'ye katkıda bulunun
```

---

## 🆘 Sorun mu Yaşıyorsunuz?

### 1. Kurulum Hataları
```bash
# Python versiyonu
python3 --version  # 3.8+ olmalı

# Pip güncelle
pip install --upgrade pip

# Paketleri yeniden kur
pip install -r requirements.txt --force-reinstall
```

### 2. Telegram Çalışmıyor
```bash
# Bot token test
curl https://api.telegram.org/bot<TOKEN>/getMe

# Mesaj gönderme test
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=Test"
```

### 3. GitHub API Hatası
```bash
# Token doğrula
python3 test-config.py

# Model değiştir (daha hafif)
# config.py → GITHUB_MODEL = "gpt-4o-mini"
```

---

## 🎓 Daha Fazla Öğren

📚 **Okumanız Gerekenler:**
- `OPTIMIZATION.md` → Filtreleme stratejileri
- `STRATEGY.md` → CVE bulma taktikleri
- `KULLANIM.md` → Detaylı kullanım

🔗 **Faydalı Linkler:**
- CVE Form: https://cveform.mitre.org/
- CVSS Calculator: https://www.first.org/cvss/calculator/3.1
- WordPress Security: https://developer.wordpress.org/plugins/security/

---

## ✅ Başlamaya Hazır mısınız?

```bash
# 1. Kurulum yaptınız mı?
./setup.sh

# 2. Test ettiniz mi?
python3 test-config.py

# 3. Strateji seçtiniz mi?
./quick-start.sh

# 4. İlk tarama!
python3 scanner.py

# 5. Telegram'ı kontrol edin! 📱
```

---

**🎯 Başarılar! İlk CVE'niz yakında gelecek!** 🏆

**⚠️ Unutmayın: Etik ve yasal kurallara uyun!**
