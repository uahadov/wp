#!/usr/bin/env python3
"""
Telegram Bot - İki Yönlü İletişim & Etkileşimli AI Asistanı
Komutlar ve /m <mesaj> ile doğrudan soru sorabilirsiniz.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from openai import OpenAI
import config


class TelegramBotHandler:
    def __init__(self):
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.results_dir = Path(config.RESULTS_DIR)
        self.scanned_db = Path(config.SCANNED_PLUGINS_DB)
        self.ai_client = OpenAI(
            base_url=config.GITHUB_API_BASE,
            api_key=config.GITHUB_TOKEN,
        )

    def _get_latest_vulnerability_context(self) -> str:
        """En son bulunan zafiyetin detaylarını AI bağlamı için getir"""
        result_files = sorted(self.results_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        for r_file in result_files:
            try:
                with open(r_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("vulnerabilities_found"):
                    return json.dumps(data, indent=2, ensure_ascii=False)
            except Exception:
                continue
        return "Henüz raporlanmış aktif zafiyet verisi bulunmuyor."

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Bot başlangıç komutu"""
        welcome_message = """
🤖 <b>WordPress Zafiyet Tarayıcı & AI Güvenlik Asistanı</b>

<b>📋 Kullanılabilir Komutlar:</b>
/start - Bot bilgileri
/stats - Tarama istatistikleri
/latest - Son bulunan zafiyeti göster
/m &lt;mesaj&gt; - AI Siber Güvenlik Uzmanına Soru Sor!
/list - Bulunan tüm zafiyetli pluginler
/status - Sistem durumu
/help - Yardım menüsü

<b>💬 AI Soru Sor (Örnekler):</b>
• <code>/m Son zafiyeti cURL ile nasıl test edebilirim?</code>
• <code>/m SQL Injection için yama önerin nedir?</code>
• <code>/m Bulunan eklentide RCE açığı var mı?</code>
"""
        await update.message.reply_text(welcome_message, parse_mode="HTML")

    async def ai_ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/m <mesaj> komutu ile AI'a soru sor"""
        if not context.args:
            await update.message.reply_text(
                "⚠️ Lütfen AI'a sormak istediğiniz soruyu yazın.\n\n<b>Örnek:</b>\n<code>/m Son zafiyeti nasıl doğrulayabilirim?</code>",
                parse_mode="HTML"
            )
            return

        user_query = " ".join(context.args)
        status_msg = await update.message.reply_text("🤖 <i>AI Uzmanı yanıt hazırlıyor...</i>", parse_mode="HTML")

        # Zafiyet bağlamını al
        vuln_context = self._get_latest_vulnerability_context()

        system_prompt = f"""Sen kıdemli bir WordPress Siber Güvenlik Uzmanısın ve Kullanıcının Yardımcı Asistanısın.
Aşağıda taranan ve tespit edilen son eklenti zafiyet raporu yer almaktadır:

--- SON ZAFIYET BAĞLAMI ---
{vuln_context[:3000]}
--- BAĞLAM SONU ---

Kullanıcının sorusuna teknik olarak DDOĞRU, KESİN, NET ve ETİK kurallara uygun yanıt ver.
Eğer soru son bulunan zafiyet ile ilgiliyse rapordaki PoC, dosya konumu ve zafiyetli kod verilerine dayanarak detaylandır."""

        try:
            response = self.ai_client.chat.completions.create(
                model=config.GITHUB_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.3,
                max_tokens=1500
            )

            ai_answer = response.choices[0].message.content

            formatted_response = f"🤖 <b>AI Güvenlik Uzmanı Yanıtı:</b>\n\n{ai_answer}"

            # Mesaj uzunluğunu kontrol et
            if len(formatted_response) > 4096:
                await status_msg.edit_text(formatted_response[:4090], parse_mode="HTML")
            else:
                await status_msg.edit_text(formatted_response, parse_mode="HTML")

        except Exception as e:
            await status_msg.edit_text(f"❌ AI Yanıt Hatası: {e}")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """İstatistikleri göster"""
        try:
            if self.scanned_db.exists():
                with open(self.scanned_db, "r", encoding="utf-8") as f:
                    scanned = json.load(f)

                total = len(scanned)
                with_vulns = sum(1 for p in scanned.values() if p.get("found_vulnerabilities"))
                result_files = list(self.results_dir.glob("*.json"))

                message = f"""
📊 <b>Tarama İstatistikleri</b>

📦 Toplam Taranan Plugin: <b>{total}</b>
🚨 Doğrulanmış Zafiyet Bulunan: <b>{with_vulns}</b>
💾 Kayıtlı Rapor Sayısı: <b>{len(result_files)}</b>
🕐 Rapor Tarihi: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
            else:
                message = "❌ Henüz kayıtlı tarama verisi bulunmuyor."

            await update.message.reply_text(message, parse_mode="HTML")

        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")

    async def latest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Son bulunan zafiyeti göster"""
        try:
            result_files = sorted(self.results_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
            
            target_data = None
            for r_file in result_files:
                with open(r_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("vulnerabilities_found"):
                    target_data = data
                    break

            if not target_data:
                await update.message.reply_text("❌ Henüz doğrulanmış zafiyetli plugin bulunamadı.")
                return

            vuln = target_data["vulnerabilities_found"][0]
            slug = target_data.get("plugin_slug", "")
            dl_link = f"https://downloads.wordpress.org/plugin/{slug}.{target_data.get('plugin_version','')}.zip"

            message = f"""
🚨 <b>SON DOĞRULANMIŞ ZAFIYET</b>

📦 <b>Plugin:</b> {target_data['plugin_name']} (v{target_data['plugin_version']})
🔗 <b>İndirme Linki:</b> {dl_link}
🕐 <b>Tarih:</b> {target_data['scan_timestamp']}

🔍 <b>Zafiyet Türü:</b> {vuln['type']}
🔥 <b>Önem / CVSS:</b> {vuln['severity']} (CVSS: {vuln.get('cvss_score', 'N/A')})
📍 <b>Konum:</b> <code>{vuln.get('location', vuln.get('file', 'N/A'))}</code>

💻 <b>Zafiyetli Kod:</b>
<code>{vuln.get('vulnerable_code', 'N/A')[:250]}</code>

🧪 <b>Test Komutu (PoC):</b>
<code>{vuln.get('poc_command', 'N/A')}</code>

💬 <b>Detaylı Soru Sor:</b>
<code>/m {target_data['plugin_name']} zafiyetini detaylandır</code>
"""
            await update.message.reply_text(message, parse_mode="HTML")

        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tüm zafiyetleri listele"""
        try:
            result_files = list(self.results_dir.glob("*.json"))
            vulnerable_plugins = []

            for result_file in result_files:
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if data.get("vulnerabilities_found"):
                    vulnerable_plugins.append({
                        "name": data["plugin_name"],
                        "version": data["plugin_version"],
                        "count": len(data["vulnerabilities_found"]),
                        "date": data["scan_timestamp"]
                    })

            if not vulnerable_plugins:
                await update.message.reply_text("❌ Zafiyet tespit edilen eklenti bulunamadı.")
                return

            message = f"📋 <b>Zafiyet Bulunan Eklentiler ({len(vulnerable_plugins)} adet)</b>\n\n"
            for idx, plugin in enumerate(vulnerable_plugins, 1):
                message += f"{idx}. <b>{plugin['name']}</b> v{plugin['version']}\n"
                message += f"   • {plugin['count']} Zafiyet | {plugin['date']}\n\n"

            await update.message.reply_text(message, parse_mode="HTML")

        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {e}")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sistem durumu"""
        message = """
🔄 <b>Sistem Durumu</b>
✅ Bot Aktif
✅ AI Asistanı Hazır (/m)
✅ Bildirim Sistemi Aktif
"""
        await update.message.reply_text(message, parse_mode="HTML")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yardım menüsü"""
        await self.start_command(update, context)


def start_bot():
    """Bot'u başlat"""
    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    handler = TelegramBotHandler()

    application.add_handler(CommandHandler("start", handler.start_command))
    application.add_handler(CommandHandler("m", handler.ai_ask_command))
    application.add_handler(CommandHandler("stats", handler.stats_command))
    application.add_handler(CommandHandler("latest", handler.latest_command))
    application.add_handler(CommandHandler("list", handler.list_command))
    application.add_handler(CommandHandler("status", handler.status_command))
    application.add_handler(CommandHandler("help", handler.help_command))

    print("🤖 Telegram Bot & AI Asistanı Başlatılıyor...")
    print(f"📱 Chat ID: {config.TELEGRAM_CHAT_ID}")
    print("✅ Bot Hazır! Telegram'dan /m <sorunuz> yazarak AI ile konuşabilirsiniz.")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    start_bot()
