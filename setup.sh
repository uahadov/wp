#!/bin/bash
# WordPress Vulnerability Scanner Kurulum Scripti
# Ubuntu 22.04 için

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║    WordPress Plugin Vulnerability Scanner - Setup         ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "📋 Sistem bilgileri kontrol ediliyor..."
echo "OS: $(lsb_release -d | cut -f2)"
echo "RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo ""

# Swap kontrolü
SWAP_SIZE=$(free -h | awk '/^Swap:/ {print $2}')
echo "💾 Swap: $SWAP_SIZE"

if [ "$SWAP_SIZE" = "0B" ]; then
    echo ""
    echo "⚠️  Swap alanı bulunamadı!"
    read -p "2GB swap oluşturmak ister misiniz? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 Swap oluşturuluyor..."
        sudo fallocate -l 2G /swapfile
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile
        sudo swapon /swapfile
        echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
        echo "✅ Swap oluşturuldu"
    fi
fi

echo ""
echo "📦 Sistem paketleri güncelleniyor..."
sudo apt update

echo ""
echo "📦 Gerekli paketler kuruluyor..."
sudo apt install -y python3 python3-pip python3-venv unzip curl

echo ""
echo "🐍 Python versiyonu:"
python3 --version

echo ""
echo "📁 Proje dizinleri oluşturuluyor..."
mkdir -p work results logs

echo ""
echo "🔧 Python sanal ortamı oluşturuluyor..."
python3 -m venv venv

echo ""
echo "📦 Python paketleri kuruluyor..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "⚙️  Yapılandırma dosyası hazırlanıyor..."
if [ ! -f "config.py.bak" ]; then
    cp config.py config.py.bak
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    YAPILANDIRMA                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

read -p "GitHub AI Models API Token: " GITHUB_TOKEN
read -p "Telegram Bot Token: " TELEGRAM_BOT_TOKEN
read -p "Telegram Chat ID (varsayılan: 6532122431): " TELEGRAM_CHAT_ID
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-6532122431}

# config.py dosyasını güncelle
sed -i "s/your_github_token_here/$GITHUB_TOKEN/" config.py
sed -i "s/your_telegram_bot_token_here/$TELEGRAM_BOT_TOKEN/" config.py
sed -i "s/6532122431/$TELEGRAM_CHAT_ID/" config.py

echo ""
echo "✅ Yapılandırma tamamlandı"

echo ""
echo "🧪 Yapılandırma test ediliyor..."
chmod +x test-config.py
python3 test-config.py

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  KURULUM TAMAMLANDI! ✅                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📌 Kullanım:"
echo ""
echo "   # Sanal ortamı aktifleştir"
echo "   source venv/bin/activate"
echo ""
echo "   # Taramayı başlat"
echo "   python3 scanner.py"
echo ""
echo "📌 Otomatik tarama için (her gün saat 02:00):"
echo ""
echo "   crontab -e"
echo "   # Ekle:"
echo "   0 2 * * * cd $(pwd) && ./venv/bin/python3 scanner.py >> logs/scanner.log 2>&1"
echo ""
echo "📁 Sonuçlar: ./results/"
echo "📋 Loglar: ./logs/"
echo ""
echo "⚠️  Etik kurallara uygun kullanın!"
echo ""
