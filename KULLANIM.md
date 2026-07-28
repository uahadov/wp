# WordPress Vulnerability Scanner - Kullanım Kılavuzu

## Hızlı Başlangıç

### 1. Sunucuya Dosyaları Yükleyin

```bash
# Sunucunuza SSH ile bağlanın
ssh kullanici@sunucu-ip

# Proje dizinini oluşturun
mkdir -p ~/wordpress-vuln-scanner
cd ~/wordpress-vuln-scanner

# Dosyaları buraya yükleyin (SCP, SFTP veya git ile)
```

### 2. Kurulumu Yapın

```bash
# Setup script'ini çalıştırılabilir yapın
chmod +x setup.sh

# Kurulumu başlatın
./setup.sh
```

Kurulum sırasında sizden istenecekler:
- **GitHub AI Models API Token**: [GitHub Models](https://github.com/marketplace/models) sayfasından alabilirsiniz
- **Telegram Bot Token**: @BotFather'a `/newbot` yazarak alın
- **Telegram Chat ID**: Sizin chat ID'niz (6532122431)

### 3. İlk Taramayı Çalıştırın

```bash
# Sanal ortamı aktifleştirin
source venv/bin/activate

# Taramayı başlatın
python3 scanner.py
```

## Telegram Bot Kurulumu

### Bot Oluşturma

1. Telegram'da @BotFather'ı açın
2. `/newbot` komutunu gönderin
3. Bot için bir isim verin (örnek: "WordPress Vuln Scanner")
4. Bot için bir kullanıcı adı verin (örnek: "my_vuln_scanner_bot")
5. Size verilen token'ı not edin

### Chat ID Bulma

Chat ID'nizi zaten biliyorsunuz: **6532122431**

Ancak eğer değiştirmek isterseniz:

```bash
# Bot'unuza bir mesaj gönderin
# Sonra şu URL'yi tarayıcıda açın:
https://api.telegram.org/bot<BOT_TOKEN>/getUpdates

# JSON içinde "chat":{"id":123456789} şeklinde bulacaksınız
```

## GitHub AI Models API Token Alma

1. [GitHub Models](https://github.com/marketplace/models) sayfasına gidin
2. Oturum açın
3. "Get API Key" veya benzeri butona tıklayın
4. Token'ı kopyalayın

Ücretsiz kullanım limitleri:
- GPT-4o: 15 request/dakika
- GPT-4o-mini: 15 request/dakika

## Ayarları Değiştirme

`config.py` dosyasını düzenleyebilirsiniz:

```python
# Tarama ayarları
PLUGINS_PER_SCAN = 5  # Her seferinde kaç plugin taransın?

# Model seçimi
GITHUB_MODEL = "gpt-4o"  # veya "gpt-4o-mini" (daha hızlı ama az detaylı)
```

## Otomatik Tarama (Cron)

Her gün otomatik tarama için:

```bash
# Crontab düzenleyiciyi açın
crontab -e

# Şunu ekleyin (her gün saat 02:00):
0 2 * * * cd /home/kullanici/wordpress-vuln-scanner && ./venv/bin/python3 scanner.py >> logs/scanner.log 2>&1

# Her 6 saatte bir:
0 */6 * * * cd /home/kullanici/wordpress-vuln-scanner && ./venv/bin/python3 scanner.py >> logs/scanner.log 2>&1

# Her Pazartesi saat 09:00:
0 9 * * 1 cd /home/kullanici/wordpress-vuln-scanner && ./venv/bin/python3 scanner.py >> logs/scanner.log 2>&1
```

## Sonuçları İnceleme

```bash
# Sonuç dosyalarını listele
ls -lh results/

# Son sonucu oku
cat results/*.json | tail -n 50

# JSON'u güzel formatta görüntüle
python3 -m json.tool results/en-son-dosya.json
```

## Zafiyet Bulduğunuzda Ne Yapmalısınız?

### 1. Doğrulama
- Zafiyeti manuel olarak test edin
- Gerçekten exploit edilebilir mi kontrol edin
- False positive olabilir, dikkatli olun

### 2. Responsible Disclosure
```
Adım 1: Plugin geliştiricisine özel e-posta gönderin
        - Zafiyeti detaylı açıklayın
        - Exploit senaryosu verin
        - Çözüm önerisi sunun
        - 90 gün süre tanıyın

Adım 2: 90 gün bekleyin
        - Geliştirici zafiyeti düzeltsin
        - Güncelleme yayınlansın

Adım 3: CVE başvurusu yapın
        - https://cveform.mitre.org/
        - Tüm detayları verin
        - Referanslar ekleyin
```

### 3. CVE Başvurusu

CVE almak için gerekenler:
- ✅ Doğrulanmış zafiyet
- ✅ Detaylı teknik açıklama
- ✅ CVSS skoru
- ✅ Etkilenen versiyon bilgisi
- ✅ Çözüm önerisi/patch
- ✅ Responsible disclosure süreci tamamlanmış

## Performans Optimizasyonu

### RAM 1.5GB ile En İyi Ayarlar

```python
# config.py
PLUGINS_PER_SCAN = 3  # Aynı anda 3 plugin
GITHUB_MODEL = "gpt-4o-mini"  # Daha hafif model
```

### Swap Kullanımını İzleme

```bash
# Swap kullanımını kontrol et
free -h

# Sürekli izle
watch -n 2 free -h

# Swap kullanımı %80'i geçerse PLUGINS_PER_SCAN değerini düşürün
```

## Sorun Giderme

### "ModuleNotFoundError" Hatası
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "Rate limit exceeded" Hatası
```bash
# config.py içinde:
PLUGINS_PER_SCAN = 2  # Daha az plugin tara
# veya time.sleep() süresini artırın
```

### Telegram Mesaj Gitmiyor
```bash
# Bot token'ı test et
curl https://api.telegram.org/bot<TOKEN>/getMe

# Chat ID'yi test et
curl https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=Test
```

### "Out of Memory" Hatası
```bash
# Swap artırın
sudo swapoff /swapfile
sudo rm /swapfile
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Güvenlik İpuçları

1. **API Anahtarlarını Koruyun**
   - `config.py` dosyasını git'e eklemeyin
   - Dosya izinlerini kontrol edin: `chmod 600 config.py`

2. **Sonuçları Güvende Tutun**
   - `results/` klasörünü başkalarıyla paylaşmayın
   - Hassas bilgiler içerebilir

3. **Yasal Çerçevede Kalın**
   - Sadece araştırma amaçlı kullanın
   - Başkalarının sistemlerini izinsiz test etmeyin
   - Responsible disclosure prensibine uyun

## Yardım ve Destek

Sorun yaşıyorsanız:

1. Log dosyalarını kontrol edin: `tail -f logs/scanner.log`
2. Verbose mode ile çalıştırın: `python3 scanner.py --verbose` (ileride eklenecek)
3. Config dosyanızı tekrar kontrol edin

## Başarı İpuçları

- 🎯 **Popüler ama az güncellenen pluginlere odaklanın**
- 🔍 **Eski versiyonları da tarayın** (WordPress.org'dan manuel indirme gerekir)
- 📊 **Sonuçları düzenli inceleyin** - AI bazen false positive verir
- 🤝 **Geliştiricilerle iyi ilişki kurun** - CVE sürecinde yardımcı olurlar
- 📚 **CVE veri tabanını inceleyin** - benzer zafiyetleri öğrenin

İyi avlar! 🎉
