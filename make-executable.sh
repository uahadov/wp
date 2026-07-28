#!/bin/bash
# Tüm scriptleri çalıştırılabilir yap

echo "🔧 Scriptler çalıştırılabilir yapılıyor..."

chmod +x setup.sh
chmod +x quick-start.sh
chmod +x create-package.sh
chmod +x start-bot.sh
chmod +x stop-bot.sh
chmod +x scanner.py
chmod +x telegram_bot.py
chmod +x test-config.py

echo "✅ Tamamlandı!"
echo ""
echo "Artık şunları çalıştırabilirsiniz:"
echo "  ./setup.sh          - Kurulum"
echo "  ./quick-start.sh    - Tarama (menü)"
echo "  ./start-bot.sh      - Telegram bot başlat"
echo "  ./stop-bot.sh       - Telegram bot durdur"
echo "  ./scanner.py        - Direkt tarama"
echo "  ./test-config.py    - API test"
