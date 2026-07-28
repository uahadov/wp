# 📁 Dosya Yapısı ve Kullanım Rehberi

## 🚀 BAŞLANGIÇ DOSYALARI

### ⭐ **HIZLI-BASLANGIC.md** ← BURADAN BAŞLAYIN!
En önemli dosya! 5 dakikada kurulum ve ilk tarama.

### **setup.sh** ← İLK ÇALIŞTIRIN
Otomatik kurulum scripti. Tüm bağımlılıkları kurar.
```bash
chmod +x setup.sh
./setup.sh
```

### **test-config.py** ← SONRA BU
API keylerini ve Telegram botunu test eder.
```bash
python3 test-config.py
```

### **quick-start.sh** ← TARAMA İÇİN BU
İnteraktif menü ile farklı stratejileri seçin.
```bash
chmod +x quick-start.sh
./quick-start.sh
```

---

## 📘 DÖKÜMANTASYON

### **README.md**
Genel bilgiler, kurulum özeti, lisans.

### **KULLANIM.md**
Detaylı kullanım kılavuzu, cron kurulumu, sorun giderme.

### **OPTIMIZATION.md** ⭐ ÖNEMLİ
Filtreleme sistemi, hedefleme stratejisi, başarı oranları.
→ Bu dosyayı okuyun, %10-15 başarı oranının sırrı burada!

### **STRATEGY.md** ⭐ ÇOK ÖNEMLİ
CVE bulma stratejileri, hedef seçimi, manuel doğrulama.
→ İlk CVE'niz için bu dosyayı mutlaka okuyun!

### **TRANSFER.md**
Dosyaları sunucuya aktarma yöntemleri (ZIP, Git, SCP).

---

## 🔧 ANA PYTHON DOSYALARI

### **scanner.py** ← ANA PROGRAM
Ana tarama scripti. Tüm süreci koordine eder.
**YENİ:** Zafiyet bulana kadar devam eder!
```bash
python3 scanner.py
```

### **telegram_bot.py** ← YENİ! 🤖
İki yönlü Telegram bot. Komutlarla etkileşim.
```bash
./start-bot.sh  # Başlat
./stop-bot.sh   # Durdur
```

### **config.py** ← YAPILANDIRMA
API keyler, filtreleme kriterleri, tüm ayarlar burada.
**NOT:** Kurulum sırasında setup.sh otomatik doldurur.

### **plugin_analyzer.py**
- WordPress.org'dan plugin bulma
- Hedefli filtreleme
- İndirme ve kod tarama
- Taranan plugin takibi

### **vuln_detector.py**
- GitHub AI Models entegrasyonu
- AI ile kod analizi
- Zafiyet doğrulama
- False positive filtreleme

### **telegram_notifier.py**
- Telegram bot entegrasyonu
- Zafiyet raporları
- Tarama bildirimleri

---

## 📦 BAĞIMLILIKLAR

### **requirements.txt**
Python paketleri listesi.
```bash
pip install -r requirements.txt
```

Paketler:
- `requests` → HTTP istekleri
- `openai` → GitHub AI Models
- `python-telegram-bot` → Telegram
- `beautifulsoup4` → HTML parsing
- `lxml` → XML parsing
- `python-dotenv` → Environment değişkenler

---

## 📂 ÇALIŞMA DİZİNLERİ

### **work/** (otomatik oluşur)
Geçici çalışma dizini. İndirilen pluginler burada açılır.
→ Otomatik temizlenir

### **results/** (otomatik oluşur)
JSON raporlar burada saklanır.
```
results/
├── plugin-slug_20260729_143000.json
├── another-plugin_20260729_150000.json
└── ...
```

### **logs/** (otomatik oluşur)
Log dosyaları.
```bash
tail -f logs/scanner.log
```

### **venv/** (setup.sh oluşturur)
Python virtual environment.

---

## 💾 VERİTABANI DOSYASI

### **scanned_plugins.json**
Taranan pluginlerin veritabanı. İlk taramadan sonra oluşur.

```json
{
  "plugin-slug": {
    "version": "1.2.3",
    "scanned_at": "2026-07-29T14:30:00",
    "found_vulnerabilities": false
  }
}
```

**Neden önemli?**
- Aynı plugin'i tekrar taramayı önler
- Yeni versiyon çıktığında tekrar tarar
- Disk ve API kullanımını azaltır

**Sıfırlama:**
```bash
rm scanned_plugins.json  # Tüm pluginleri tekrar tara
```

---

## 🔒 GİZLİ DOSYALAR (.gitignore)

Bu dosyalar Git'e eklenmemeli:

- `config.py.bak` → Backup
- `.env` → Environment değişkenler
- `work/` → Geçici dosyalar
- `results/` → Hassas raporlar
- `logs/` → Log dosyaları
- `venv/` → Virtual environment
- `scanned_plugins.json` → Veritabanı

---

## 📋 YARDIMCI DOSYALAR

### **.gitignore**
Git için ignore listesi.

### **.env.example**
Örnek environment dosyası.

### **create-package.sh**
Projeyi ZIP olarak paketler.
```bash
bash create-package.sh
```

---

## 📊 KULLANIM AKIŞI

```
1. KURULUM
   setup.sh → Sistem hazır
   ↓
2. TEST
   test-config.py → API keyler çalışıyor mu?
   ↓
3. TARAMA
   quick-start.sh → Strateji seç
   veya
   scanner.py → Direkt tarama
   ↓
4. SONUÇLAR
   Telegram → Anında bildirim
   results/ → JSON raporlar
   scanned_plugins.json → Veritabanı
   ↓
5. MANUEL DOĞRULAMA
   STRATEGY.md → Nasıl doğrulanır?
   ↓
6. CVE BAŞVURUSU
   https://cveform.mitre.org/
```

---

## 🎯 HANGİ DOSYAYI NE ZAMAN OKUMALI?

### Yeni başlıyorum:
1. ✅ **HIZLI-BASLANGIC.md** (5 dk)
2. ✅ **setup.sh çalıştır** (2 dk)
3. ✅ **test-config.py çalıştır** (1 dk)
4. ✅ **quick-start.sh çalıştır** (ilk tarama!)

### Strateji öğrenmek istiyorum:
1. ✅ **STRATEGY.md** (10 dk)
2. ✅ **OPTIMIZATION.md** (10 dk)

### Sorun yaşıyorum:
1. ✅ **KULLANIM.md** → Sorun Giderme bölümü
2. ✅ **test-config.py** → API test

### Ayarları özelleştirmek istiyorum:
1. ✅ **config.py** → Filtreleme kriterleri
2. ✅ **OPTIMIZATION.md** → Hangi ayar ne işe yarar?

### İleri seviye:
1. ✅ **scanner.py** → Ana kod
2. ✅ **plugin_analyzer.py** → Filtreleme mantığı
3. ✅ **vuln_detector.py** → AI analiz mantığı

---

## 🔥 EN ÖNEMLİ 5 DOSYA

1. **HIZLI-BASLANGIC.md** → İlk adım
2. **STRATEGY.md** → CVE bulma sırları
3. **config.py** → Tüm ayarlar
4. **scanner.py** → Ana program
5. **scanned_plugins.json** → İlerleme takibi

---

## 📞 HIZLI KOMUTLAR

```bash
# Kurulum
./setup.sh

# Test
python3 test-config.py

# Tarama (interaktif)
./quick-start.sh

# Tarama (direkt)
source venv/bin/activate
python3 scanner.py

# İstatistikler
python3 -c "import json; d=json.load(open('scanned_plugins.json')); print(f'Taranan: {len(d)}')"

# Son rapor
ls -lt results/*.json | head -1

# Log izle
tail -f logs/scanner.log

# Veritabanını sıfırla
rm scanned_plugins.json

# Tüm geçici dosyaları temizle
rm -rf work/* logs/* results/*
```

---

## 🎓 ÖĞRENİM YOLU

```
Gün 1: Kurulum ve İlk Tarama
├── HIZLI-BASLANGIC.md
├── setup.sh
├── test-config.py
└── quick-start.sh → İlk zafiyet bekleniyor!

Gün 2: Strateji Öğrenme
├── STRATEGY.md
├── OPTIMIZATION.md
└── config.py düzenleme

Gün 3-7: Günlük Taramalar
├── Farklı stratejiler dene
├── Sonuçları analiz et
└── Manuel doğrulama öğren

Hafta 2+: İlk CVE'ye Doğru
├── Gerçek zafiyeti bul
├── Responsible disclosure
└── CVE başvurusu!
```

---

## ✅ KONTROL LİSTESİ

Kurulum tamamlandı mı?
- [ ] setup.sh çalıştırıldı
- [ ] API keyler girildi
- [ ] test-config.py başarılı
- [ ] Telegram'a test mesajı geldi
- [ ] venv/ oluşturuldu
- [ ] work/, results/, logs/ dizinleri var

İlk tarama yapıldı mı?
- [ ] scanner.py veya quick-start.sh çalıştırıldı
- [ ] Telegram'a bildirim geldi
- [ ] results/ klasöründe JSON var
- [ ] scanned_plugins.json oluşturuldu

Stratejileri öğrendiniz mi?
- [ ] STRATEGY.md okundu
- [ ] OPTIMIZATION.md okundu
- [ ] Hedef strateji seçildi

---

**🎯 Hazırsınız! İyi avlar!** 🏆
