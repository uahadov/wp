#!/usr/bin/env python3
"""
Telegram Bot - İki Yönlü İletişim
Komutlarla etkileşim kurabilirsiniz
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import config


class TelegramBotHandler:
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.results_dir = Path(config.RESULTS_DIR)
        self.scanned_db = Path(config.SCANNED_PLUGINS_DB)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot başlangıç komutu"""
        welcome_message = """
🤖 <b>WordPress Zafiyet Tarayıcı Bot</b>

Merhaba! Ben sizin zafiyet avcısı botunuzum.

<b>📋 Komutlar:</b>

/start - Bot bilgileri
/stats - İstatistikler
/latest - Son bulunan zafiyet
/cvss [plugin] - CVSS skoru sorgula
/list - Bulunan tüm zafiyetler
/status - Tarama durumu
/help - Yardım

<b>💬 Sorular:</b>
Herhangi bir mesaj gönderirseniz size yardımcı olurum!

Örnek: "Bu CVE değeri kaç?"
"""
        await update.message.reply_text(welcome_message, parse_mode="HTML")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """İstatistikleri göster"""
        try:
            # Taranan pluginler
            if self.scanned_db.exists():
                with open(self.scanned_db, "r", encoding="utf-8") as f:
                    scanned = json.load(f)
                
                total = len(scanned)
                with_vulns = sum(1 for p in scanned.values() if p.get("found_vulnerabilities"))
                
                # Sonuç dosyaları
                result_files = list(self.results_dir.glob("*.json"))
                
                message = f"""
📊 <b>Tarama İstatistikleri</b>

📦 Toplam taranan plugin: <b>{total}</b>
🚨 Zafiyet bulunan: <b>{with_vulns}</b>
📈 Başarı oranı: <b>{with_vulns/total*100:.1f}%</b>

💾 Kayıtlı rapor: <b>{len(result_files)}</b>

🕐 Son güncelleme: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
            else:
                message = "❌ Henüz tarama yapılmamış"
            
            await update.message.reply_text(message, parse_mode="HTML")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")
    
    async def latest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Son bulunan zafiyeti göster"""
        try:
            result_files = sorted(self.results_dir.glob("*.json"), reverse=True)
            
            if not result_files:
                await update.message.reply_text("❌ Henüz zafiyet bulunamadı")
                return
            
            # En son raporu oku
            with open(result_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not data.get("vulnerabilities_found"):
                await update.message.reply_text("❌ Son taramada zafiyet bulunamadı")
                return
            
            vuln = data["vulnerabilities_found"][0]  # İlk zafiyet
            
            message = f"""
🚨 <b>SON BULUNAN ZAFİYET</b>

📦 <b>Plugin:</b> {data['plugin_name']}
📌 <b>Versiyon:</b> {data['plugin_version']}
🕐 <b>Tarih:</b> {data['scan_timestamp']}

<b>🔍 Zafiyet Detayı:</b>
<b>Tür:</b> {vuln['type']}
<b>Önem:</b> {vuln['severity']}
<b>CVSS:</b> {vuln.get('cvss_score', 'N/A')}

<b>📄 Dosya:</b> {vuln.get('file', 'N/A')}

<b>📝 Açıklama:</b>
{vuln['description'][:200]}...
"""
            
            await update.message.reply_text(message, parse_mode="HTML")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")
    
    async def cvss_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """CVSS skoru sorgula"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "Kullanım: /cvss [plugin-adı]\nÖrnek: /cvss contact-form-7"
                )
                return
            
            plugin_name = " ".join(context.args).lower()
            
            # Sonuç dosyalarında ara
            found = []
            for result_file in self.results_dir.glob("*.json"):
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if plugin_name in data.get("plugin_slug", "").lower() or \
                   plugin_name in data.get("plugin_name", "").lower():
                    found.append(data)
            
            if not found:
                await update.message.reply_text(
                    f"❌ '{plugin_name}' için sonuç bulunamadı"
                )
                return
            
            # Sonuçları göster
            for data in found:
                if data.get("vulnerabilities_found"):
                    message = f"""
📊 <b>CVSS Skor Raporu</b>

📦 <b>Plugin:</b> {data['plugin_name']}
📌 <b>Versiyon:</b> {data['plugin_version']}

<b>🚨 Zafiyetler:</b>
"""
                    for idx, vuln in enumerate(data["vulnerabilities_found"], 1):
                        cvss = vuln.get("cvss_score", "N/A")
                        message += f"\n{idx}. {vuln['type']}\n"
                        message += f"   • CVSS: <b>{cvss}</b>\n"
                        message += f"   • Önem: {vuln['severity']}\n"
                    
                    await update.message.reply_text(message, parse_mode="HTML")
                else:
                    await update.message.reply_text(
                        f"✅ {data['plugin_name']} - Zafiyet bulunamadı"
                    )
        
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tüm bulunan zafiyetleri listele"""
        try:
            result_files = list(self.results_dir.glob("*.json"))
            
            if not result_files:
                await update.message.reply_text("❌ Henüz zafiyet bulunamadı")
                return
            
            vulnerable_plugins = []
            
            for result_file in result_files:
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if data.get("vulnerabilities_found"):
                    vulnerable_plugins.append({
                        "name": data["plugin_name"],
                        "count": len(data["vulnerabilities_found"]),
                        "date": data["scan_timestamp"]
                    })
            
            if not vulnerable_plugins:
                await update.message.reply_text("❌ Zafiyet içeren plugin bulunamadı")
                return
            
            message = f"""
📋 <b>Bulunan Zafiyetler ({len(vulnerable_plugins)} plugin)</b>

"""
            for idx, plugin in enumerate(vulnerable_plugins, 1):
                message += f"{idx}. <b>{plugin['name']}</b>\n"
                message += f"   • {plugin['count']} zafiyet\n"
                message += f"   • {plugin['date']}\n\n"
            
            await update.message.reply_text(message, parse_mode="HTML")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tarama durumu"""
        message = """
🔄 <b>Sistem Durumu</b>

✅ Bot çalışıyor
✅ API bağlantısı aktif
✅ Bildirimler açık

Yeni tarama başlatmak için sunucuda:
<code>python3 scanner.py</code>
"""
        await update.message.reply_text(message, parse_mode="HTML")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yardım mesajı"""
        help_message = """
📚 <b>Yardım ve Komutlar</b>

<b>Temel Komutlar:</b>
/start - Bot'u başlat
/help - Bu yardım mesajı
/status - Sistem durumu

<b>İstatistikler:</b>
/stats - Genel istatistikler
/list - Tüm zafiyetleri listele
/latest - Son bulunan zafiyet

<b>Sorgulama:</b>
/cvss [plugin] - CVSS skoru sorgula
Örnek: <code>/cvss contact-form</code>

<b>💬 Doğal Dil:</b>
Herhangi bir soru sorabilirsiniz:
• "Bu CVE değeri kaç?"
• "Son zafiyet neydi?"
• "Kaç plugin tarandı?"

Bot size otomatik yanıt verecek! 🤖
"""
        await update.message.reply_text(help_message, parse_mode="HTML")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Normal mesajları işle (AI benzeri)"""
        try:
            text = update.message.text.lower()
            
            # Basit anahtar kelime eşleştirme
            if any(word in text for word in ["cvss", "cve", "skor", "puan"]):
                await update.message.reply_text(
                    "CVSS skoru sorgulamak için:\n/cvss [plugin-adı]\n\nÖrnek: /cvss contact-form"
                )
            
            elif any(word in text for word in ["son", "latest", "en son", "yeni"]):
                await self.latest_command(update, context)
            
            elif any(word in text for word in ["istatistik", "stats", "durum", "kaç"]):
                await self.stats_command(update, context)
            
            elif any(word in text for word in ["liste", "list", "hepsi", "tümü"]):
                await self.list_command(update, context)
            
            elif any(word in text for word in ["yardım", "help", "nasıl"]):
                await self.help_command(update, context)
            
            else:
                await update.message.reply_text(
                    "🤔 Ne demek istediğinizi anlayamadım.\n\n"
                    "Komutlar için: /help\n"
                    "İstatistikler için: /stats\n"
                    "Son zafiyet için: /latest"
                )
        
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")


def start_bot():
    """Bot'u başlat"""
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    handler = TelegramBotHandler()
    
    # Komutları kaydet
    application.add_handler(CommandHandler("start", handler.start_command))
    application.add_handler(CommandHandler("stats", handler.stats_command))
    application.add_handler(CommandHandler("latest", handler.latest_command))
    application.add_handler(CommandHandler("cvss", handler.cvss_command))
    application.add_handler(CommandHandler("list", handler.list_command))
    application.add_handler(CommandHandler("status", handler.status_command))
    application.add_handler(CommandHandler("help", handler.help_command))
    
    # Normal mesajlar
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler.handle_message))
    
    print("🤖 Telegram Bot başlatılıyor...")
    print(f"📱 Chat ID: {config.TELEGRAM_CHAT_ID}")
    print("✅ Bot hazır! Telegram'dan mesaj gönderebilirsiniz.")
    print("\nBot'u durdurmak için Ctrl+C")
    
    # Bot'u çalıştır
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    start_bot()
