# 🤖 Telegram Bot Kullanım Kılavuzu

## Ne Değişti? 🎉

### ✅ **YENİ ÖZELLİKLER:**

1. **İki Yönlü İletişim**: Artık bot'a mesaj gönderebilir, komut verebilirsiniz!
2. **Zafiyet Bulana Kadar Devam**: Scanner zafiyet bulana kadar durmaz!
3. **Akıllı Temizlik**: Zafiyet bulunan pluginler saklanır, diğerleri silinir!

---

## 🤖 Telegram Bot Komutları

### Temel Komutlar:

```
/start   - Bot'u başlat ve hoş geldin mesajı
/help    - Komutlar listesi
/status  - Sistem durumu kontrolü
```

### İstatistik Komutları:

```
/stats   - Genel tarama istatistikleri
         → Kaç plugin tarandı?
         → Kaç zafiyet bulundu?
         → Başarı oranı nedir?

/list    - Tüm bulunan zafiyetleri listele
         → Zafiyet içeren pluginler
         → Tarih bilgisi
         → Zafiyet sayıları

/latest  - En son bulunan zafiyeti göster
         → Detaylı bilgi
         → CVSS skoru
         → Dosya ve satır bilgisi
```

### Sorgulama Komutları:

```
/cvss [plugin-adı]  - Belirli bir plugin'in CVSS skorunu sorgula
                      
Örnekler:
/cvss contact-form
/cvss security-plugin
/cvss my-plugin-name
```

### Doğal Dil Desteği:

Bot'a normal mesaj da gönderebilirsiniz! Otomatik algılar:

```
"Bu CVE değeri kaç?"          → CVSS komutunu önerir
"Son zafiyet neydi?"          → /latest çalıştırır
"Kaç plugin tarandı?"         → /stats gösterir
"Tüm zafiyetleri göster"      → /list çalıştırır
"Yardım lazım"                → /help gösterir
```

---

## 🚀 Bot'u Başlatma

### 1. Bot'u Arka Planda Çalıştır:

```bash
chmod +x start-bot.sh
./start-bot.sh
```

**Çıktı:**
```
✅ Bot başarıyla başlatıldı!
📱 PID: 12345
📋 Log: tail -f logs/telegram_bot.log

🎯 Telegram'dan botunuza mesaj gönderin:
   /start - Bot'u başlat
```

### 2. Bot Loglarını İzle:

```bash
tail -f logs/telegram_bot.log
```

### 3. Bot'u Durdur:

```bash
chmod +x stop-bot.sh
./stop-bot.sh
```

---

## 🎯 Yeni Scanner Davranışı

### ❌ **ESKİ DAVRANIŞ:**
```
5 plugin tara
  ↓
Zafiyet bul veya bulma
  ↓
DUR
```

### ✅ **YENİ DAVRANIŞ:**
```
Plugin tara
  ↓
Zafiyet bulamadın mı?
  ↓
YENİ PLUGIN GETIR VE DEVAM ET
  ↓
Zafiyet buldun mu?
  ↓
DUR VE BİLDİR! 🎉
```

**Sonuç:** Mutlaka zafiyet bulana kadar çalışır!

---

## 🗑️ Akıllı Temizlik Sistemi

### Zafiyet BULUNAN Plugin:
```
Plugin tarandı
  ↓
Zafiyet bulundu! 🚨
  ↓
Plugin dosyaları SAKLANDI
  ↓
work/plugin-name/ → Silinmedi ✅
```

### Zafiyet BULUNMAYAN Plugin:
```
Plugin tarandı
  ↓
Zafiyet bulunamadı ❌
  ↓
Plugin dosyaları SİLİNDİ
  ↓
work/plugin-name/ → Temizlendi 🗑️
```

**Neden?**
- Disk tasarrufu (zafiyet olmayanları saklamanın anlamı yok)
- Zafiyet bulunanlar manuel inceleme için saklanır
- work/ klasörü büyümez

---

## 📱 Kullanım Senaryoları

### Senaryo 1: İstatistik Kontrol

```
Siz (Telegram'da): /stats

Bot:
📊 Tarama İstatistikleri

📦 Toplam taranan plugin: 47
🚨 Zafiyet bulunan: 3
📈 Başarı oranı: 6.4%

💾 Kayıtlı rapor: 3

🕐 Son güncelleme: 2026-07-29 14:30:00
```

### Senaryo 2: CVSS Sorgulama

```
Siz: /cvss contact-form-7

Bot:
📊 CVSS Skor Raporu

📦 Plugin: Contact Form 7
📌 Versiyon: 5.2.0

🚨 Zafiyetler:

1. SQL Injection
   • CVSS: 8.5
   • Önem: High

2. XSS (Stored)
   • CVSS: 6.8
   • Önem: Medium
```

### Senaryo 3: Son Zafiyet

```
Siz: /latest

Bot:
🚨 SON BULUNAN ZAFİYET

📦 Plugin: Old Security Plugin
📌 Versiyon: 1.2.3
🕐 Tarih: 2026-07-29 12:15:00

🔍 Zafiyet Detayı:
Tür: Remote Code Execution
Önem: Critical
CVSS: 9.8

📄 Dosya: admin/upload.php

📝 Açıklama:
Unauthenticated file upload vulnerability allows...
```

### Senaryo 4: Doğal Dil

```
Siz: Bu CVE değeri kaç?

Bot:
CVSS skoru sorgulamak için:
/cvss [plugin-adı]

Örnek: /cvss contact-form
```

---

## 🔄 Bot + Scanner Birlikte Kullanım

### Terminal 1: Bot'u Başlat
```bash
./start-bot.sh
```

### Terminal 2: Scanner'ı Başlat
```bash
python3 scanner.py
```

### Telegram: Canlı Takip
```
Bot size bildirimleri gönderir
  ↓
Siz komutlarla sorgular yaparsınız
  ↓
İki yönlü iletişim! 🎉
```

---

## 🛠️ Cron ile Otomatik Tarama + Bot

### Crontab Ayarı:

```bash
crontab -e

# Bot'u sistem başlangıcında başlat
@reboot cd /path/to/wordpress-vuln-scanner && ./start-bot.sh

# Her gün saat 02:00'de tarama yap
0 2 * * * cd /path/to/wordpress-vuln-scanner && ./venv/bin/python3 scanner.py >> logs/scanner.log 2>&1
```

**Sonuç:**
- Bot 7/24 çalışır
- Günlük otomatik tarama
- Zafiyet bulunca Telegram'a bildirim
- Siz bot'a komut göndererek sorgulama yapabilirsiniz

---

## 📊 Bot İstatistikleri

### Real-time İzleme:

```bash
# Bot logları
tail -f logs/telegram_bot.log

# Scanner logları
tail -f logs/scanner.log

# İkisini birden
tail -f logs/*.log
```

---

## 💡 İpuçları

### 1. Bot Çalışıyor mu Kontrol:
```bash
cat telegram_bot.pid
ps aux | grep telegram_bot
```

### 2. Bot Yeniden Başlat:
```bash
./stop-bot.sh
./start-bot.sh
```

### 3. Scanner Çalışırken Bot Komutları:
Scanner çalışırken de bot'a komut gönderebilirsiniz!
- `/stats` → Anlık istatistik
- `/list` → Şimdiye kadar bulunanlar
- `/latest` → En son bulunan

### 4. Bot Bildirimleri Test:
```python
# Test scripti
python3 << EOF
import asyncio
from telegram import Bot
import config

async def test():
    bot = Bot(config.TELEGRAM_BOT_TOKEN)
    await bot.send_message(
        chat_id=config.TELEGRAM_CHAT_ID,
        text="🧪 Test mesajı - Bot çalışıyor!"
    )

asyncio.run(test())
EOF
```

---

## 🐛 Sorun Giderme

### Bot başlamıyor:
```bash
# Logları kontrol et
cat logs/telegram_bot.log

# Token'ı kontrol et
python3 test-config.py

# Manuel başlat (debug için)
source venv/bin/activate
python3 telegram_bot.py
```

### Bot yanıt vermiyor:
```bash
# Bot çalışıyor mu?
cat telegram_bot.pid
ps -p $(cat telegram_bot.pid)

# Yeniden başlat
./stop-bot.sh && ./start-bot.sh
```

### Scanner durmuyor:
```bash
# Scanner PID bul
ps aux | grep scanner.py

# Durdur
kill <PID>

# Veya zorla
pkill -f scanner.py
```

---

## 🎉 Özet

### Artık Yapabilecekleriniz:

1. ✅ Bot'a Telegram'dan komut gönder
2. ✅ CVSS skorlarını sorgula
3. ✅ İstatistikleri anlık gör
4. ✅ Doğal dille konuş ("Bu CVE değeri kaç?")
5. ✅ Scanner zafiyet bulana kadar çalışsın
6. ✅ Zafiyet bulunanlar saklansin, diğerleri silinsin

### Başlangıç Komutu:

```bash
# Bot'u başlat
./start-bot.sh

# Scanner'ı başlat (başka terminal)
python3 scanner.py

# Telegram'dan botunuza:
/start
/help
```

**Artık tam otomatik zafiyet avcılığı sisteminiz var!** 🎯🏆
