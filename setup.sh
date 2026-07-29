#!/bin/bash
# WordPress Vulnerability Scanner Kurulum Scripti
# Ubuntu 22.04 / Linux için (Non-interactive / Tam Otomatik)

set -e

# Interaktif promtları engelle (DEBIAN_FRONTEND)
export DEBIAN_FRONTEND=noninteractive

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║    WordPress Plugin Vulnerability Scanner - Setup         ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

echo "📋 Sistem bilgileri kontrol ediliyor..."
if command -v lsb_release &> /dev/null; then
    echo "OS: $(lsb_release -d | cut -f2)"
fi
echo "RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo ""

# Swap kontrolü (Sessiz ve Otomatik)
SWAP_SIZE=$(free -h | awk '/^Swap:/ {print $2}')
echo "💾 Swap: $SWAP_SIZE"

if [ "$SWAP_SIZE" = "0B" ] || [ -z "$SWAP_SIZE" ]; then
    echo "📦 Swap alanı bulunamadı, 2GB Swap otomatik oluşturuluyor..."
    if [ "$EUID" -eq 0 ] || command -v sudo &> /dev/null; then
        SUDO_CMD=""
        if [ "$EUID" -ne 0 ]; then SUDO_CMD="sudo"; fi
        $SUDO_CMD fallocate -l 2G /swapfile 2>/dev/null || $SUDO_CMD dd if=/dev/zero of=/swapfile bs=1M count=2048
        $SUDO_CMD chmod 600 /swapfile
        $SUDO_CMD mkswap /swapfile
        $SUDO_CMD swapon /swapfile
        echo '/swapfile none swap sw 0 0' | $SUDO_CMD tee -a /etc/fstab > /dev/null
        echo "✅ Swap oluşturuldu"
    fi
fi

echo ""
echo "📦 Sistem paketleri güncelleniyor..."
SUDO_CMD=""
if [ "$EUID" -ne 0 ]; then SUDO_CMD="sudo"; fi
$SUDO_CMD apt-get update -y

echo ""
echo "📦 Gerekli paketler kuruluyor..."
$SUDO_CMD apt-get install -y python3 python3-pip python3-venv unzip curl

echo ""
echo "🐍 Python versiyonu:"
python3 --version

echo ""
echo "📁 Proje dizinleri oluşturuluyor..."
mkdir -p work results logs

echo ""
echo "🔧 Python sanal ortamı oluşturuluyor..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

echo ""
echo "📦 Python paketleri kuruluyor..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "⚙️  Yapılandırma (.env) kontrol ediliyor..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "⚠️  .env dosyası oluşturuldu (.env.example şablonundan türetildi)."
    else
        cat <<EOT > .env
GITHUB_TOKEN=your_github_token_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=6532122431
GITHUB_MODEL=gpt-4o
PLUGINS_PER_SCAN=5
EOT
        echo "✅ .env dosyası varsayılan anahtarlarla oluşturuldu."
    fi
else
    echo "✅ .env dosyası mevcut."
fi

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
echo "📁 Sonuçlar: ./results/"
echo "📋 Loglar: ./logs/"
echo ""
