# Dosyaları Sunucuya Aktarma Kılavuzu

## Yöntem 1: ZIP ile Aktarma (En Kolay)

### Windows'tan:

1. **wordpress-vuln-scanner** klasörünü sağ tık → "Sıkıştır" → ZIP oluşturun

2. **WinSCP** veya **FileZilla** ile sunucuya bağlanın:
   ```
   Host: sunucu-ip-adresi
   Port: 22
   Username: kullanıcı-adınız
   Password: şifreniz
   ```

3. ZIP dosyasını sunucuya yükleyin

4. SSH ile sunucuya bağlanın ve:
   ```bash
   # ZIP'i açın
   unzip wordpress-vuln-scanner.zip
   cd wordpress-vuln-scanner
   
   # Kuruluma geçin
   chmod +x setup.sh
   ./setup.sh
   ```

## Yöntem 2: Git ile Aktarma (Önerilen)

### Eğer GitHub/GitLab kullanıyorsanız:

1. **Yeni bir PRIVATE repository oluşturun** (public yapMAYIN!)

2. Bu klasörü git repository'sine yükleyin:
   ```bash
   cd wordpress-vuln-scanner
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/kullanici/repo-adi.git
   git push -u origin main
   ```

3. Sunucuda:
   ```bash
   git clone https://github.com/kullanici/repo-adi.git
   cd repo-adi
   chmod +x setup.sh
   ./setup.sh
   ```

## Yöntem 3: SCP ile Doğrudan Aktarma

### Linux/Mac'ten:

```bash
# Tüm klasörü aktar
scp -r wordpress-vuln-scanner kullanici@sunucu-ip:~/

# Sunucuya bağlan
ssh kullanici@sunucu-ip

# Kuruluma geç
cd wordpress-vuln-scanner
chmod +x setup.sh
./setup.sh
```

### Windows'tan (PowerShell):

```powershell
# pscp kullanarak (PuTTY ile gelir)
pscp -r wordpress-vuln-scanner kullanici@sunucu-ip:/home/kullanici/
```

---

## ⚠️ ÖNEMLİ: Git Kullanıyorsanız

**config.py dosyasını git'e EKLEMEYİN!**

Çünkü API keyler içerecek. Zaten .gitignore ayarlandı ama dikkat edin.

---

## Kurulum Sonrası

Setup.sh çalıştırıldığında sizden istenecekler:

1. **GitHub AI Models Token** 
   - Nereden: https://github.com/marketplace/models
   - Format: `ghp_xxxxxxxxxxxx` gibi

2. **Telegram Bot Token**
   - @BotFather'dan alın
   - Format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` gibi

3. **Telegram Chat ID**
   - Sizinki: `6532122431`
   - Enter'a basarak devam edin

---

## Hızlı Test

Kurulum bittikten sonra:

```bash
source venv/bin/activate
python3 scanner.py
```

İlk tarama başlayacak ve Telegram'a bildirim gelecek! 🚀
