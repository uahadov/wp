#!/usr/bin/env python3
"""
Yapılandırma Test Scripti
API keylerini ve Telegram botunu test eder
"""

import sys
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

print("=" * 60)
print("WordPress Zafiyet Tarayıcı - Yapılandırma Testi")
print("=" * 60)
print()

# Config'i import et
try:
    import config
    print("✅ config.py dosyası bulundu")
except ImportError:
    print("❌ config.py dosyası bulunamadı!")
    sys.exit(1)

print()
print("📋 Yapılandırma Kontrolleri:")
print("-" * 60)

# 1. GitHub Token kontrolü
print("\n1️⃣  GitHub AI Models Token...")
if not config.GITHUB_TOKEN or config.GITHUB_TOKEN == "your_github_token_here":
    print("   ❌ Token ayarlanmamış!")
    print("   → .env veya config.py dosyasını düzenleyin")
    sys.exit(1)
else:
    token_display = config.GITHUB_TOKEN[:10] + "..." if len(config.GITHUB_TOKEN) > 10 else config.GITHUB_TOKEN
    print(f"   ✅ Token bulundu: {token_display}")
    
    # API testi
    try:
        print("   🔄 API bağlantısı test ediliyor...")
        from openai import OpenAI
        client = OpenAI(
            base_url=config.GITHUB_API_BASE,
            api_key=config.GITHUB_TOKEN,
        )
        
        response = client.chat.completions.create(
            model=config.GITHUB_MODEL,
            messages=[
                {"role": "user", "content": "Merhaba, test"}
            ],
            max_tokens=10
        )
        
        print("   ✅ GitHub AI Models API çalışıyor!")
        print(f"   📊 Model: {config.GITHUB_MODEL}")
        
    except Exception as e:
        print(f"   ❌ API hatası: {e}")
        print("   → Token'ı kontrol edin: https://github.com/marketplace/models")
        sys.exit(1)

# 2. Telegram Bot kontrolü
print("\n2️⃣  Telegram Bot Token...")
if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
    print("   ❌ Bot token ayarlanmamış!")
    print("   → .env dosyasında TELEGRAM_BOT_TOKEN ayarlayın")
    sys.exit(1)
else:
    bot_token_display = config.TELEGRAM_BOT_TOKEN[:10] + "..." if len(config.TELEGRAM_BOT_TOKEN) > 10 else config.TELEGRAM_BOT_TOKEN
    print(f"   ✅ Token bulundu: {bot_token_display}")
    
    # Bot testi
    try:
        print("   🔄 Bot bağlantısı test ediliyor...")
        import asyncio
        from telegram import Bot
        
        async def test_bot():
            bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
            bot_info = await bot.get_me()
            return bot_info
        
        bot_info = asyncio.run(test_bot())
        print(f"   ✅ Bot çalışıyor: @{bot_info.username}")
        
    except Exception as e:
        print(f"   ❌ Bot hatası: {e}")
        print("   → Token'ı kontrol edin")
        sys.exit(1)

# 3. Telegram Chat ID kontrolü
print("\n3️⃣  Telegram Chat ID...")
print(f"   ✅ Chat ID: {config.TELEGRAM_CHAT_ID}")

# Test mesajı gönder
try:
    print("   🔄 Test mesajı gönderiliyor...")
    
    async def send_test():
        test_bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        await test_bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text="✅ WordPress Zafiyet Tarayıcı kurulumu başarılı!\n\nSistem hazır. İlk taramayı başlatabilirsiniz.",
            parse_mode="HTML"
        )
    
    asyncio.run(send_test())
    
    print("   ✅ Test mesajı gönderildi!")
    print("   → Telegram'ı kontrol edin")
    
except Exception as e:
    print(f"   ❌ Mesaj gönderilemedi: {e}")
    print("   → Chat ID'yi kontrol edin")
    print("   ⚠️  Bu hata kurulumu etkilemez, devam edebilirsiniz")

# 4. WordPress API kontrolü
print("\n4️⃣  WordPress.org API...")
try:
    print("   🔄 API erişimi test ediliyor...")
    response = requests.get(
        config.WORDPRESS_API,
        params={
            "action": "query_plugins",
            "request[per_page]": 1,
            "request[browse]": "popular"
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("plugins"):
            print("   ✅ WordPress API erişilebilir")
            print(f"   📦 Test plugin: {data['plugins'][0]['name']}")
        else:
            print("   ⚠️  API yanıt verdi ama plugin bulunamadı")
    else:
        print(f"   ❌ API hatası: HTTP {response.status_code}")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ Bağlantı hatası: {e}")
    print("   → İnternet bağlantınızı kontrol edin")
    sys.exit(1)

# 5. Dizin kontrolleri
print("\n5️⃣  Dizin Yapısı...")
dirs = ["work", "results", "logs"]
for d in dirs:
    p = Path(d)
    if p.exists():
        print(f"   ✅ {d}/ dizini mevcut")
    else:
        print(f"   🔄 {d}/ dizini oluşturuluyor...")
        p.mkdir(exist_ok=True)
        print(f"   ✅ {d}/ oluşturuldu")

# 6. Tarama ayarları
print("\n6️⃣  Tarama Ayarları...")
print(f"   📊 Her taramada plugin sayısı: {config.PLUGINS_PER_SCAN}")
print(f"   📈 Max aktif kurulum: {config.FILTER_CRITERIA['max_active_installs']:,}")
print(f"   📉 Min aktif kurulum: {config.FILTER_CRITERIA['min_active_installs']:,}")
print(f"   ⏰ Min güncelleme: {config.FILTER_CRITERIA['min_months_since_update']} ay")
print(f"   ⏰ Max güncelleme: {config.FILTER_CRITERIA['max_months_since_update']} ay")
print(f"   ⭐ Min rating: {config.FILTER_CRITERIA['min_rating']}/100")

# Özet
print()
print("=" * 60)
print("🎉 TÜM TESTLER BAŞARILI!")
print("=" * 60)
print()
print("✅ Sistem hazır. Taramayı başlatabilirsiniz:")
print()
print("   python3 scanner.py")
print()
