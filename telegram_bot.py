#!/usr/bin/env python3
"""
Telegram Bot - İki Yönlü İletişim & Etkileşimli AI Asistanı
Komutlar ve /m <mesaj> ile doğrudan soru sorabilirsiniz.
"""

import html
import json
import logging
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from openai import OpenAI
import config

logger = logging.getLogger(__name__)


class TelegramBotHandler:
    def __init__(self):
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.results_dir = Path(config.RESULTS_DIR)
        self.scanned_db = Path(config.SCANNED_PLUGINS_DB)
        self.ai_client = OpenAI(
            base_url=config.GITHUB_API_BASE,
            api_key=config.GITHUB_TOKEN,
        )

    @staticmethod
    def _escape(text: str) -> str:
        """Telegram HTML için özel karakterleri escape et"""
        return html.escape(str(text), quote=False)

    def _get_latest_vulnerability_context(self) -> str:
        """En son bulunan zafiyetin detaylarını AI bağlamı için getir"""
        if not self.results_dir.exists():
            return "Henüz raporlanmış aktif zafiyet verisi bulunmuyor."

        result_files = sorted(
            self.results_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
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
        welcome_message = (
            "🤖 <b>WordPress Zafiyet Tarayıcı &amp; AI Güvenlik Asistanı</b>\n\n"
            "<b>📋 Kullanılabilir Komutlar:</b>\n"
            "/start - Bot bilgileri\n"
            "/stats - Tarama istatistikleri\n"
            "/latest - Son bulunan zafiyeti göster\n"
            "/m &lt;mesaj&gt; - AI Siber Güvenlik Uzmanına Soru Sor!\n"
            "/list - Bulunan tüm zafiyetli pluginler\n"
            "/status - Sistem durumu\n"
            "/help - Yardım menüsü\n\n"
            "<b>💬 AI Soru Sor (Örnekler):</b>\n"
            "• <code>/m Son zafiyeti cURL ile nasıl test edebilirim?</code>\n"
            "• <code>/m SQL Injection için yama önerin nedir?</code>\n"
            "• <code>/m Bulunan eklentide RCE açığı var mı?</code>"
        )
        await update.message.reply_text(welcome_message, parse_mode="HTML")

    async def ai_ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/m <mesaj> komutu ile AI'a soru sor"""
        if not context.args:
            await update.message.reply_text(
                "⚠️ Lütfen AI'a sormak istediğiniz soruyu yazın.\n\n"
                "<b>Örnek:</b>\n<code>/m Son zafiyeti nasıl doğrulayabilirim?</code>",
                parse_mode="HTML"
            )
            return

        user_query = " ".join(context.args)
        status_msg = await update.message.reply_text(
            "🤖 <i>AI Uzmanı yanıt hazırlıyor...</i>",
            parse_mode="HTML"
        )

        # Zafiyet bağlamını al
        vuln_context = self._get_latest_vulnerability_context()

        system_prompt = (
            "Sen kıdemli bir WordPress Siber Güvenlik Uzmanısın ve Kullanıcının Yardımcı Asistanısın.\n"
            "Aşağıda taranan ve tespit edilen son eklenti zafiyet raporu yer almaktadır:\n\n"
            "--- SON ZAFIYET BAĞLAMI ---\n"
            f"{vuln_context[:3000]}\n"
            "--- BAĞLAM SONU ---\n\n"
            "Kullanıcının sorusuna teknik olarak DOĞRU, KESİN, NET ve ETİK kurallara uygun yanıt ver.\n"
            "Eğer soru son bulunan zafiyet ile ilgiliyse rapordaki PoC, dosya konumu ve "
            "zafiyetli kod verilerine dayanarak detaylandır."
        )

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

            # HTML karakterlerini escape et (AI yanıtı kötü HTML içerebilir)
            escaped_answer = self._escape(ai_answer)
            formatted_response = f"🤖 <b>AI Güvenlik Uzmanı Yanıtı:</b>\n\n{escaped_answer}"

            # Mesaj uzunluğunu kontrol et
            if len(formatted_response) > 4096:
                formatted_response = formatted_response[:4090] + "\n<i>...(kırpıldı)</i>"

            await status_msg.edit_text(formatted_response, parse_mode="HTML")

        except Exception as e:
            logger.error(f"AI yanıt hatası: {e}", exc_info=True)
            await status_msg.edit_text(
                f"❌ <b>AI Yanıt Hatası:</b> {self._escape(str(e)[:200])}",
                parse_mode="HTML"
            )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """İstatistikleri göster"""
        try:
            if self.scanned_db.exists():
                with open(self.scanned_db, "r", encoding="utf-8") as f:
                    scanned = json.load(f)

                if not isinstance(scanned, dict):
                    scanned = {}

                total = len(scanned)
                with_vulns = sum(
                    1 for p in scanned.values()
                    if isinstance(p, dict) and p.get("found_vulnerabilities")
                )
                result_files = list(self.results_dir.glob("*.json")) if self.results_dir.exists() else []

                message = (
                    "📊 <b>Tarama İstatistikleri</b>\n\n"
                    f"📦 Toplam Taranan Plugin: <b>{total}</b>\n"
                    f"🚨 Doğrulanmış Zafiyet Bulunan: <b>{with_vulns}</b>\n"
                    f"💾 Kayıtlı Rapor Sayısı: <b>{len(result_files)}</b>\n"
                    f"🕐 Rapor Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                message = "❌ Henüz kayıtlı tarama verisi bulunmuyor."

            await update.message.reply_text(message, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Stats hatası: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Hata: {self._escape(str(e))}", parse_mode="HTML")

    async def latest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Son bulunan zafiyeti göster"""
        try:
            if not self.results_dir.exists():
                await update.message.reply_text("❌ Henüz doğrulanmış zafiyetli plugin bulunamadı.")
                return

            result_files = sorted(
                self.results_dir.glob("*.json"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            target_data = None
            for r_file in result_files:
                try:
                    with open(r_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and data.get("vulnerabilities_found"):
                        target_data = data
                        break
                except Exception:
                    continue

            if not target_data:
                await update.message.reply_text("❌ Henüz doğrulanmış zafiyetli plugin bulunamadı.")
                return

            vuln = target_data["vulnerabilities_found"][0]
            slug = target_data.get("plugin_slug", "")
            version = target_data.get("plugin_version", "")
            dl_link = (
                f"https://downloads.wordpress.org/plugin/{slug}.{version}.zip"
                if slug and version else "N/A"
            )

            vuln_code_raw = str(vuln.get("vulnerable_code", "N/A"))[:250]
            poc_raw = str(vuln.get("poc_command", "N/A"))

            message = (
                "🚨 <b>SON DOĞRULANMIŞ ZAFİYET</b>\n\n"
                f"📦 <b>Plugin:</b> {self._escape(target_data.get('plugin_name', 'Unknown'))} "
                f"(v{self._escape(version)})\n"
                f"🔗 <b>İndirme Linki:</b> {self._escape(dl_link)}\n"
                f"🕐 <b>Tarih:</b> {self._escape(target_data.get('scan_timestamp', 'N/A'))}\n\n"
                f"🔍 <b>Zafiyet Türü:</b> {self._escape(vuln.get('type', 'N/A'))}\n"
                f"🔥 <b>Önem / CVSS:</b> {self._escape(vuln.get('severity', 'N/A'))} "
                f"(CVSS: {self._escape(str(vuln.get('cvss_score', 'N/A')))})\n"
                f"📍 <b>Konum:</b> <code>{self._escape(vuln.get('location', vuln.get('file', 'N/A')))}</code>\n\n"
                f"💻 <b>Zafiyetli Kod:</b>\n<code>{self._escape(vuln_code_raw)}</code>\n\n"
                f"🧪 <b>Test Komutu (PoC):</b>\n<code>{self._escape(poc_raw)}</code>\n\n"
                f"💬 <b>Detaylı Soru Sor:</b>\n"
                f"<code>/m {self._escape(target_data.get('plugin_name', ''))} zafiyetini detaylandır</code>"
            )
            await update.message.reply_text(message, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Latest hatası: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Hata: {self._escape(str(e))}", parse_mode="HTML")

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Tüm zafiyetleri listele"""
        try:
            if not self.results_dir.exists():
                await update.message.reply_text("❌ Zafiyet tespit edilen eklenti bulunamadı.")
                return

            result_files = list(self.results_dir.glob("*.json"))
            vulnerable_plugins = []

            for result_file in result_files:
                try:
                    with open(result_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and data.get("vulnerabilities_found"):
                        vulnerable_plugins.append({
                            "name": data.get("plugin_name", "Unknown"),
                            "version": data.get("plugin_version", "?"),
                            "count": len(data["vulnerabilities_found"]),
                            "date": data.get("scan_timestamp", "N/A")
                        })
                except Exception:
                    continue

            if not vulnerable_plugins:
                await update.message.reply_text("❌ Zafiyet tespit edilen eklenti bulunamadı.")
                return

            message = f"📋 <b>Zafiyet Bulunan Eklentiler ({len(vulnerable_plugins)} adet)</b>\n\n"
            for idx, plugin in enumerate(vulnerable_plugins, 1):
                message += (
                    f"{idx}. <b>{self._escape(plugin['name'])}</b> v{self._escape(plugin['version'])}\n"
                    f"   • {plugin['count']} Zafiyet | {self._escape(plugin['date'])}\n\n"
                )
                # Telegram limiti - çok uzunsa bölünecek
                if len(message) > 3800 and idx < len(vulnerable_plugins):
                    message += f"<i>... ve {len(vulnerable_plugins) - idx} plugin daha</i>"
                    break

            await update.message.reply_text(message, parse_mode="HTML")

        except Exception as e:
            logger.error(f"List hatası: {e}", exc_info=True)
            await update.message.reply_text(f"❌ Hata: {self._escape(str(e))}", parse_mode="HTML")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Sistem durumu"""
        # Gerçek durum kontrolü yap
        ai_status = "✅ Hazır" 
        try:
            # API'ye ping atmak yerine sadece client'ın var olup olmadığını kontrol et
            if not config.GITHUB_TOKEN or config.GITHUB_TOKEN == "your_github_token_here":
                ai_status = "❌ Token Eksik"
        except Exception:
            ai_status = "⚠️ Bilinmiyor"

        db_status = "✅ Aktif" if self.scanned_db.exists() else "⚠️ Henüz oluşturulmadı"
        results_count = len(list(self.results_dir.glob("*.json"))) if self.results_dir.exists() else 0

        message = (
            "🔄 <b>Sistem Durumu</b>\n\n"
            "✅ Bot Aktif\n"
            f"🤖 AI Asistanı: {ai_status}\n"
            f"💾 Veritabanı: {db_status}\n"
            f"📊 Kayıtlı Rapor: {results_count} adet\n"
            f"🕐 Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await update.message.reply_text(message, parse_mode="HTML")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Yardım menüsü"""
        await self.start_command(update, context)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Global hata yakalayıcı"""
        logger.error(f"Telegram bot hatası: {context.error}", exc_info=context.error)


def start_bot():
    """Bot'u başlat"""
    if not config.TELEGRAM_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("❌ TELEGRAM_BOT_TOKEN .env dosyasında ayarlanmamış!")
        return

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    handler = TelegramBotHandler()

    application.add_handler(CommandHandler("start", handler.start_command))
    application.add_handler(CommandHandler("m", handler.ai_ask_command))
    application.add_handler(CommandHandler("stats", handler.stats_command))
    application.add_handler(CommandHandler("latest", handler.latest_command))
    application.add_handler(CommandHandler("list", handler.list_command))
    application.add_handler(CommandHandler("status", handler.status_command))
    application.add_handler(CommandHandler("help", handler.help_command))

    # Global hata yakalayıcı
    application.add_error_handler(handler.error_handler)

    print("🤖 Telegram Bot & AI Asistanı Başlatılıyor...")
    print(f"📱 Chat ID: {config.TELEGRAM_CHAT_ID}")
    print("✅ Bot Hazır! Telegram'dan /m <sorunuz> yazarak AI ile konuşabilirsiniz.")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    start_bot()
