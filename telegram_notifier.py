# -*- coding: utf-8 -*-
"""
Telegram bildirim modülü
Bulunan zafiyetleri Telegram üzerinden bildirir
"""

import asyncio
from typing import Dict
from telegram import Bot
from telegram.error import TelegramError
import config


class TelegramNotifier:
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.chat_id = config.TELEGRAM_CHAT_ID

    async def send_message(self, message: str):
        """Telegram'a mesaj gönder"""
        try:
            # Mesaj çok uzunsa böl (Telegram limiti 4096 karakter)
            if len(message) > 4096:
                chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
                for chunk in chunks:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=chunk,
                        parse_mode="HTML"
                    )
                    await asyncio.sleep(1)
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode="HTML"
                )
            return True
        except TelegramError as e:
            print(f"\u274c Telegram gönderme hatası: {e}")
            return False

    def format_vulnerability_report(self, results: Dict) -> str:
        """Zafiyet raporunu Telegram mesajı olarak formatla"""

        if not results["vulnerabilities_found"]:
            message = (
                "\U0001f50d <b>WordPress Plugin Taramas\u0131</b>\n\n"
                f"\U0001f4e6 <b>Plugin:</b> {results['plugin_name']}\n"
                f"\U0001f4cc <b>Versiyon:</b> {results['plugin_version']}\n"
                f"\U0001f550 <b>Tarih:</b> {results['scan_timestamp']}\n\n"
                f"\u2705 <b>Sonu\u00e7:</b> Zafiyet bulunamad\u0131\n"
                f"\U0001f4ca {results['total_files_analyzed']} dosya analiz edildi"
            )
            return message

        # Zafiyet bulundu!
        summary = results["summary"]

        message = (
            "\U0001f6a8 <b>ZAF\u0130YET BULUNDU!</b> \U0001f6a8\n\n"
            f"\U0001f4e6 <b>Plugin:</b> {results['plugin_name']}\n"
            f"\U0001f4cc <b>Versiyon:</b> {results['plugin_version']}\n"
            f"\U0001f550 <b>Tarih:</b> {results['scan_timestamp']}\n\n"
            f"\U0001f4ca <b>\u00d6zet:</b>\n"
            f"\u2022 Toplam Zafiyet: {summary['total_vulnerabilities']}\n"
        )

        # Severity bilgisi
        if "by_severity" in summary:
            message += "\n<b>\u00d6nem Da\u011f\u0131l\u0131m\u0131:</b>\n"
            for severity, count in summary["by_severity"].items():
                if severity == "Critical":
                    sev_emoji = "\U0001f534"
                elif severity == "High":
                    sev_emoji = "\U0001f7e0"
                elif severity == "Medium":
                    sev_emoji = "\U0001f7e1"
                else:
                    sev_emoji = "\U0001f7e2"
                message += f"{sev_emoji} {severity}: {count}\n"

        message += "\n" + "=" * 40 + "\n\n"

        # Her zafiyet için detay
        for idx, vuln in enumerate(results["vulnerabilities_found"], 1):
            sev = vuln.get("severity", "Low")
            if sev == "Critical":
                severity_emoji = "\U0001f534"
            elif sev == "High":
                severity_emoji = "\U0001f7e0"
            elif sev == "Medium":
                severity_emoji = "\U0001f7e1"
            else:
                severity_emoji = "\U0001f7e2"

            desc = vuln.get("description", "")[:200]
            exploit = vuln.get("exploit_scenario", "Belirtilmemi\u015f")[:300]
            rec = vuln.get("recommendation", "Belirtilmemi\u015f")[:200]
            file_loc = vuln.get("file", vuln.get("location", "N/A"))

            message += (
                f"<b>{idx}. {vuln['type']}</b> {severity_emoji}\n\n"
                f"<b>\u00d6nem:</b> {sev} (CVSS: {vuln.get('cvss_score', 'N/A')})\n"
                f"<b>Dosya:</b> {file_loc}\n"
                f"<b>A\u00e7\u0131klama:</b> {desc}...\n\n"
                f"<b>Exploit Senaryosu:</b>\n{exploit}...\n\n"
                f"<b>\u00c7\u00f6z\u00fcm \u00d6nerisi:</b>\n{rec}...\n\n"
                + "-" * 40 + "\n\n"
            )

        # CVE başvuru bilgisi
        message += (
            "\n<b>\U0001f4cc Sonraki Ad\u0131mlar:</b>\n"
            "1. Plugin geli\u015ftiricisine \u00f6zel olarak bildir\n"
            "2. 90 g\u00fcn bekle (Responsible Disclosure)\n"
            "3. CVE ba\u015fvurusu yap: https://cveform.mitre.org/\n\n"
            "<b>\u26a0\ufe0f \u00d6NEML\u0130:</b> Bu bilgileri sorumlu bir \u015fekilde kullan\u0131n!"
        )

        return message

    def send_vulnerability_report(self, results: Dict):
        """Zafiyet raporunu gönder (Python 3.12 uyumlu asyncio.run)"""
        message = self.format_vulnerability_report(results)
        success = asyncio.run(self.send_message(message))
        if success:
            print("\u2705 Telegram bildirimi gönderildi")
        else:
            print("\u274c Telegram bildirimi gönderilemedi")
        return success

    def send_scan_start(self, plugin_count: int):
        """Tarama başlangıç bildirimi"""
        message = (
            "\U0001f504 <b>WordPress Zafiyet Tamas\u0131 Ba\u015flad\u0131</b>\n\n"
            f"\U0001f4e6 {plugin_count} plugin analiz edilecek\n"
            f"\u23f1\ufe0f Tahmini s\u00fcre: {plugin_count * 2} dakika\n\n"
            "Bulgular i\u00e7in beklemede..."
        )
        asyncio.run(self.send_message(message))

    def send_scan_complete(self, total_plugins: int, vulns_found: int):
        """Tarama tamamlanma bildirimi"""
        result_text = "\U0001f389 Ba\u015far\u0131lar!" if vulns_found > 0 else "Sonraki taramaya haz\u0131r."
        message = (
            "\u2705 <b>Tarama Tamamland\u0131</b>\n\n"
            f"\U0001f4e6 Analiz edilen plugin: {total_plugins}\n"
            f"\U0001f6a8 Zafiyet bulunan plugin: {vulns_found}\n\n"
            f"{result_text}"
        )
        asyncio.run(self.send_message(message))
