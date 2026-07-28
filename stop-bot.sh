#!/bin/bash
# Telegram Bot'u durdur

set -e

PID_FILE="telegram_bot.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "❌ Bot çalışmıyor (PID dosyası bulunamadı)"
    exit 1
fi

BOT_PID=$(cat "$PID_FILE")

if ps -p $BOT_PID > /dev/null 2>&1; then
    echo "🛑 Bot durduruluyor (PID: $BOT_PID)..."
    kill $BOT_PID
    rm "$PID_FILE"
    echo "✅ Bot durduruldu"
else
    echo "⚠️  Bot zaten çalışmıyor"
    rm "$PID_FILE"
fi
