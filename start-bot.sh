#!/bin/bash
# Telegram Bot'u başlat (arka planda)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🤖 Telegram Bot başlatılıyor..."

# Virtual environment kontrolü
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment bulunamadı!"
    echo "Önce ./setup.sh çalıştırın"
    exit 1
fi

# Activate venv
source venv/bin/activate

# PID dosyası kontrolü
PID_FILE="telegram_bot.pid"

if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "⚠️  Bot zaten çalışıyor (PID: $OLD_PID)"
        echo ""
        read -p "Yeniden başlatmak ister misiniz? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🔄 Eski bot durduruluyor..."
            kill $OLD_PID
            sleep 2
        else
            echo "Bot çalışmaya devam ediyor"
            exit 0
        fi
    fi
fi

# Bot'u arka planda başlat
echo "🚀 Bot başlatılıyor..."
nohup python3 telegram_bot.py > logs/telegram_bot.log 2>&1 &
BOT_PID=$!

# PID'yi kaydet
echo $BOT_PID > "$PID_FILE"

sleep 2

# Kontrol et
if ps -p $BOT_PID > /dev/null; then
    echo "✅ Bot başarıyla başlatıldı!"
    echo "📱 PID: $BOT_PID"
    echo "📋 Log: tail -f logs/telegram_bot.log"
    echo ""
    echo "🎯 Telegram'dan botunuza mesaj gönderin:"
    echo "   /start - Bot'u başlat"
    echo "   /help - Komutlar"
    echo "   /stats - İstatistikler"
    echo ""
    echo "🛑 Bot'u durdurmak için:"
    echo "   ./stop-bot.sh"
else
    echo "❌ Bot başlatılamadı!"
    echo "Log'u kontrol edin: cat logs/telegram_bot.log"
    exit 1
fi
