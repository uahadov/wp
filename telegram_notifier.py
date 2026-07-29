# -*- coding: utf-8 -*-
"""
Telegram bildirim modülü
Bulunan zafiyetleri Telegram üzerinden detaylı şekilde bildirir
"""

import asyncio
from typing import Dict
from telegram import Bot
from telegram.error import TelegramError
import config


class TelegramNotifier:
    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID

    async def _send_async_message(self, message: str):
        """Telegram'a mesaj gönder (Her çağrıda temiz Bot instance)"""
        bot = Bot(token=self.token)
        try:
            # Mesaj çok uzunsa böl (Telegram limiti 4096 karakter)
            if len(message) > 4096:
                chunks = [message[i:i+4090] for i in range(0, len(message), 4090)]
                for chunk in chunks:
                    await bot.send_message(
                        chat_id=self.chat_id,
                        text=chunk,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
                    await asyncio.sleep(0.5)
            else:
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
            return True
        except TelegramError as e:
            print(f"❌ Telegram gönderme hatası: {e}")
            return False
        finally:
            await bot.shutdown()

    def send_message(self, message: str) -> bool:
        """Senkron olarak async mesaj göndericiyi tetikle"""
        try:
            return asyncio.run(self._send_async_message(message))
        except Exception as e:
            print(f"❌ Telegram mesaj hatası: {e}")
            return False

    def format_vulnerability_report(self, results: Dict) -> str:
        """Zafiyet raporunu Telegram mesajı olarak ÇOK DETAYLI formatla"""

        slug = results.get("plugin_slug", "")
        download_url = f"https://downloads.wordpress.org/plugin/{slug}.{results.get('plugin_version', '')}.zip"

        if not results.get("vulnerabilities_found"):
            message = (
                "🔍 <b>WordPress Plugin Taraması</b>\n\n"
                f"📦 <b>Plugin:</b> {results['plugin_name']}\n"
                f"📌 <b>Versiyon:</b> {results['plugin_version']}\n"
                f"🕐 <b>Tarih:</b> {results['scan_timestamp']}\n\n"
                f"✅ <b>Sonuç:</b> Doğrulanabilir Zafiyet Bulunamadı\n"
                f"📊 {results['total_files_analyzed']} dosya analiz edildi"
            )
            return message

        summary = results["summary"]

        message = (
            "🚨 <b>KRİTİK ZAFIYET BULUNDU!</b> 🚨\n\n"
            f"📦 <b>Plugin:</b> {results['plugin_name']}\n"
            f"📌 <b>Versiyon:</b> {results['plugin_version']}\n"
            f"🔗 <b>İndirme Linki:</b> {download_url}\n"
            f"🕐 <b>Tarih:</b> {results['scan_timestamp']}\n\n"
            f"📊 <b>Toplam Doğrulanmış Zafiyet:</b> {summary['total_vulnerabilities']}\n"
        )

        if "by_severity" in summary:
            message += "\n<b>Önem Dağılımı:</b>\n"
            for severity, count in summary["by_severity"].items():
                sev_emoji = "🔴" if severity == "Critical" else "🟠" if severity == "High" else "🟡" if severity == "Medium" else "🟢"
                message += f"{sev_emoji} {severity}: {count}\n"

        message += "\n" + "=" * 35 + "\n\n"

        # Her zafiyet için DETAYLI açıklama
        for idx, vuln in enumerate(results["vulnerabilities_found"], 1):
            sev = vuln.get("severity", "High")
            severity_emoji = "🔴" if sev == "Critical" else "🟠" if sev == "High" else "🟡"
            cvss = vuln.get("cvss_score", "N/A")
            wf_cat = vuln.get("wordfence_category", "Wordfence Verified Exploit")
            location = vuln.get("location", vuln.get("file", "N/A"))
            vulnerable_code = vuln.get("vulnerable_code", "Belirtilmemiş")
            desc = vuln.get("description", "Açıklama yok")
            exploit = vuln.get("exploit_scenario", "Senaryo yok")
            poc = vuln.get("poc_command", "cURL/HTTP isteği yok")
            rec = vuln.get("recommendation", "Öneri yok")

            message += (
                f"<b>{idx}. {vuln['type']}</b> {severity_emoji}\n"
                f"🛡️ <b>Wordfence Kategori:</b> {wf_cat}\n"
                f"🔥 <b>CVSS Skor:</b> {cvss} ({sev})\n"
                f"📍 <b>Konum:</b> <code>{location}</code>\n\n"
                f"💻 <b>Zafiyetli Kod Parçası:</b>\n"
                f"<code>{vulnerable_code[:300]}</code>\n\n"
                f"📝 <b>Açıklama:</b>\n{desc}\n\n"
                f"🎯 <b>Exploit Senaryosu:</b>\n{exploit}\n\n"
                f"🧪 <b>Manuel Test Komutu (PoC):</b>\n"
                f"<code>{poc}</code>\n\n"
                f"🛠️ <b>Çözüm Önerisi:</b>\n{rec}\n\n"
                + "-" * 35 + "\n\n"
            )

        message += (
            "<b>📌 Sonraki Adımlar:</b>\n"
            "1. Raporu local <code>results/</code> klasöründen doğrulayın.\n"
            "2. Manuel cURL PoC komutu ile zafiyeti test edin.\n"
            "3. Plugin geliştiricisine özel bildirim yapın (Responsible Disclosure)."
        )

        return message

    def send_vulnerability_report(self, results: Dict) -> bool:
        """Zafiyet raporunu gönder"""
        message = self.format_vulnerability_report(results)
        success = self.send_message(message)
        if success:
            print("✅ Telegram bildirimi detaylı olarak gönderildi")
        else:
            print("❌ Telegram bildirimi gönderilemedi")
        return success

    def send_scan_start(self, plugin_count: int):
        """Tarama başlangıç bildirimi"""
        message = (
            "🔄 <b>WordPress Zafiyet Taraması Başladı</b>\n\n"
            f"📦 {plugin_count} hedef plugin analiz edilecek\n"
            "Bulgular bekleniyor..."
        )
        self.send_message(message)

    def send_scan_complete(self, total_plugins: int, vulns_found: int):
        """Tarama tamamlanma bildirimi"""
        result_text = "🎉 Doğrulanmış zafiyet(ler) bulundu!" if vulns_found > 0 else "Tüm tarama tamamlandı."
        message = (
            "✅ <b>Tarama Tamamlandı</b>\n\n"
            f"📦 Analiz Edilen: {total_plugins}\n"
            f"🚨 Zafiyet Bulunan: {vulns_found}\n\n"
            f"{result_text}"
        )
        self.send_message(message)
