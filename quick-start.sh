#!/bin/bash
# Hızlı Başlangıç Menüsü

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

clear

echo -e "${PURPLE}"
cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║     WordPress Zafiyet Tarayıcı - Hızlı Başlangıç         ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Virtual environment kontrolü
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment bulunamadı!${NC}"
    echo -e "${YELLOW}Önce setup.sh çalıştırın:${NC}"
    echo "   ./setup.sh"
    exit 1
fi

# Activate venv
source venv/bin/activate

echo -e "${CYAN}📊 Sistem Durumu:${NC}"
echo ""

# Taranan plugin sayısı
if [ -f "scanned_plugins.json" ]; then
    SCANNED_COUNT=$(python3 -c "import json; print(len(json.load(open('scanned_plugins.json'))))" 2>/dev/null || echo "0")
    echo -e "${GREEN}✅ Daha önce taranan plugin: $SCANNED_COUNT${NC}"
else
    echo -e "${YELLOW}⚠️  Henüz tarama yapılmamış${NC}"
fi

# Sonuç sayısı
if [ -d "results" ]; then
    RESULTS_COUNT=$(ls -1 results/*.json 2>/dev/null | wc -l)
    echo -e "${GREEN}✅ Kayıtlı sonuç: $RESULTS_COUNT${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Hangi stratejiyle tarama yapmak istersiniz?${NC}"
echo ""
echo "  1) 🧟 Zombi Pluginler (1.5-3 yıl güncellenmemiş) - ÖNERİLEN"
echo "  2) 🛡️  Güvenlik Pluginleri (güvenlik ironisi)"
echo "  3) 📎 Dosya Yükleme (kritik zafiyetler)"
echo "  4) 💳 E-Ticaret & Ödeme (yüksek değer)"
echo "  5) 👤 Admin Panel (privilege escalation)"
echo "  6) 📝 Form Pluginleri (SQL Injection)"
echo "  7) 🎲 Rastgele (varsayılan ayarlar)"
echo "  8) ⚙️  Özel Ayarlar (config.py düzenle)"
echo "  9) 📊 İstatistikler Göster"
echo "  0) 🚪 Çıkış"
echo ""
read -p "Seçiminiz (1-9): " choice

case $choice in
    1)
        echo -e "${GREEN}🧟 Zombi Plugin stratejisi seçildi${NC}"
        python3 << EOF
import config
config.FILTER_CRITERIA['min_months_since_update'] = 18
config.FILTER_CRITERIA['max_months_since_update'] = 36
config.FILTER_CRITERIA['max_active_installs'] = 30000
with open('config.py', 'r') as f:
    content = f.read()
    content = content.replace('"min_months_since_update": 3,', '"min_months_since_update": 18,')
    content = content.replace('"max_months_since_update": 48,', '"max_months_since_update": 36,')
with open('config.py', 'w') as f:
    f.write(content)
print("✅ Ayarlar güncellendi")
EOF
        python3 scanner.py
        ;;
    
    2)
        echo -e "${GREEN}🛡️  Güvenlik Plugin stratejisi seçildi${NC}"
        python3 << EOF
import config
config.FILTER_CRITERIA['prioritize_categories'] = ["security", "firewall", "anti-spam", "backup"]
config.FILTER_CRITERIA['min_months_since_update'] = 6
EOF
        python3 scanner.py
        ;;
    
    3)
        echo -e "${GREEN}📎 Dosya Yükleme stratejisi seçildi${NC}"
        python3 scanner.py
        echo -e "${YELLOW}Not: Dosya yükleme manuel kontrol gerektirir${NC}"
        ;;
    
    4)
        echo -e "${GREEN}💳 E-Ticaret stratejisi seçildi${NC}"
        python3 scanner.py
        ;;
    
    5)
        echo -e "${GREEN}👤 Admin Panel stratejisi seçildi${NC}"
        python3 scanner.py
        ;;
    
    6)
        echo -e "${GREEN}📝 Form Plugin stratejisi seçildi${NC}"
        python3 scanner.py
        ;;
    
    7)
        echo -e "${GREEN}🎲 Rastgele tarama başlatılıyor${NC}"
        python3 scanner.py
        ;;
    
    8)
        echo -e "${CYAN}⚙️  Config düzenleniyor...${NC}"
        ${EDITOR:-nano} config.py
        echo ""
        read -p "Şimdi taramayı başlat? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 scanner.py
        fi
        ;;
    
    9)
        echo -e "${CYAN}📊 İstatistikler:${NC}"
        echo ""
        python3 << EOF
import json
import os
from datetime import datetime

# Taranan pluginler
if os.path.exists('scanned_plugins.json'):
    with open('scanned_plugins.json') as f:
        scanned = json.load(f)
    
    total = len(scanned)
    with_vulns = sum(1 for p in scanned.values() if p.get('found_vulnerabilities'))
    
    print(f"📦 Toplam taranan plugin: {total}")
    print(f"🚨 Zafiyet bulunan: {with_vulns}")
    if total > 0:
        print(f"📈 Başarı oranı: {with_vulns/total*100:.1f}%")
    print()
    
    # En son tarama
    if scanned:
        latest = max(scanned.values(), key=lambda x: x.get('scanned_at', ''))
        print(f"🕐 Son tarama: {latest.get('scanned_at', 'N/A')}")
else:
    print("❌ Henüz tarama yapılmamış")

# Sonuç dosyaları
if os.path.exists('results'):
    results = [f for f in os.listdir('results') if f.endswith('.json')]
    print(f"\n💾 Kayıtlı rapor sayısı: {len(results)}")
    
    if results:
        print("\n📋 Son 5 rapor:")
        for r in sorted(results, reverse=True)[:5]:
            print(f"   • {r}")
EOF
        echo ""
        read -p "Enter'a basın..." 
        ;;
    
    0)
        echo -e "${CYAN}Çıkış yapılıyor...${NC}"
        exit 0
        ;;
    
    *)
        echo -e "${RED}❌ Geçersiz seçim!${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Tarama tamamlandı!${NC}"
echo ""
echo -e "${CYAN}Sonraki adımlar:${NC}"
echo "  • results/ klasöründeki raporları inceleyin"
echo "  • Telegram'dan gelen bildirimleri kontrol edin"
echo "  • Zafiyetleri manuel olarak doğrulayın"
echo "  • CVE başvurusunu hazırlayın"
echo ""
