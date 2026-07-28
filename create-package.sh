#!/bin/bash
# Projeyi paketleme scripti
# Sunucuya aktarmak için ZIP oluşturur

echo "📦 WordPress Vulnerability Scanner paketleniyor..."

# Tarih damgası
DATE=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="wordpress-vuln-scanner-${DATE}.zip"

# Gereksiz dosyaları temizle
rm -rf work/ results/ logs/ venv/ __pycache__/ *.pyc

# ZIP oluştur (config.py'daki hassas bilgileri temizleyerek)
zip -r "$PACKAGE_NAME" . \
    -x "*.git*" \
    -x "*__pycache__*" \
    -x "*.pyc" \
    -x "venv/*" \
    -x "work/*" \
    -x "results/*" \
    -x "logs/*" \
    -x "*.zip"

echo "✅ Paket oluşturuldu: $PACKAGE_NAME"
echo ""
echo "📋 Sonraki adımlar:"
echo "   1. $PACKAGE_NAME dosyasını sunucuya yükleyin"
echo "   2. Sunucuda: unzip $PACKAGE_NAME"
echo "   3. cd wordpress-vuln-scanner"
echo "   4. chmod +x setup.sh && ./setup.sh"
echo ""
