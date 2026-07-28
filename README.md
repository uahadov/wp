<<<<<<< HEAD
# WordPress Plugin Vulnerability Scanner

WordPress pluginlerini otomatik olarak tarayan, AI destekli zafiyet analizi yapan ve Telegram üzerinden bildirim gönderen sistem.

## Özellikler

- ✅ **Hedefli tarama**: Az bilinen ve eski pluginleri otomatik bulur
- ✅ **Akıllı filtreleme**: Popülerlik, güncelleme tarihi, kategori bazlı önceliklendirme
- ✅ **En son versiyon garantisi**: Her zaman en güncel versiyonu indirir
- ✅ **Tekrar tarama önleme**: Aynı plugin'i veritabanında takip eder
- ✅ **GitHub AI Models API** ile derin kod analizi
- ✅ **Çoklu zafiyet tespiti**: SQL Injection, XSS, CSRF, Path Traversal, RCE, File Upload
- ✅ **False positive filtreleme**: AI ile zafiyet doğrulama
- ✅ **Telegram bildirimi**: Anında detaylı raporlama
- ✅ **Düşük RAM kullanımı**: 1.5GB RAM ile çalışır

## Kurulum

### 1. Sistem Gereksinimleri

```bash
# Python 3.8+ kurulu olmalı
python3 --version

# Gerekli sistem paketleri
sudo apt update
sudo apt install -y python3-pip python3-venv unzip
```

### 2. Swap Alanı Oluşturma (Önerilen)

```bash
# 2GB swap oluştur
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Kalıcı yapma
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. Proje Kurulumu

```bash
cd wordpress-vuln-scanner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Yapılandırma

`config.py` dosyasını düzenleyin:
- GitHub AI Models API token'ınızı girin
- Telegram bot token'ınızı girin
- Telegram chat ID'nizi girin

### 5. Çalıştırma

```bash
# Tek seferlik tarama
python3 scanner.py

# Taranan pluginleri görmek için
cat scanned_plugins.json

# Veritabanını sıfırlayıp yeniden taramak için
rm scanned_plugins.json

# Cron ile otomatik (her gün saat 02:00)
crontab -e
# Ekleyin: 0 2 * * * cd /path/to/wordpress-vuln-scanner && ./venv/bin/python3 scanner.py >> logs/scanner.log 2>&1
```

## Güvenlik ve Etik

⚠️ **ÖNEMLİ**: Bu araç sadece eğitim ve araştırma amaçlıdır.

- Bulduğunuz zafiyetleri plugin geliştiricilerine önce özel olarak bildirin
- 90 gün süre tanıyın (responsible disclosure)
- CVE başvurusu için: https://cveform.mitre.org/
- Yasal sınırlar içinde kalın

## Lisans

MIT License - Eğitim ve araştırma amaçlı
=======
# wp
>>>>>>> aa9328819c0c8ccea0c24db7333cdb8726f5d034
