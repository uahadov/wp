# -*- coding: utf-8 -*-
"""
Telegram bildirim modülü
Bulunan zafiyetleri Telegram üzerinden detaylı şekilde bildirir
"""

import asyncio
import html
from typing import Dict
from telegram import Bot
from telegram.error import TelegramError
import config


class TelegramNotifier:
    def __init__(self):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID

    @staticmethod
    def _escape(text: str) -> str:
        """Telegram HTML parse_mode için özel karakterleri kaçış yaptır (XSS / parse hatası önleme)"""
        if not text:
            return ""
        return html.escape(str(text), quote=False)

    async def _send_async_message(self, message: str):
        """Telegram'a mesaj gönder (Her çağrıda temiz Bot instance)"""
        bot = Bot(token=self.token)
        try:
            # Mesaj çok uzunsa böl (Telegram limiti 4096 karakter)
            if len(message) > 4096:
                # Parçalara böl - HTML tag'larını kırmamaya özen göster
                chunks = []
                current = ""
                for line in message.splitlines(keepends=True):
                    if len(current) + len(line) > 4090:
                        if current:
                            chunks.append(current)
                        current = line
                    else:
                        current += line
                if current:
                    chunks.append(current)

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
        except RuntimeError as e:
            # Zaten çalışan bir event loop varsa (örn. Jupyter/asyncio context)
            if "running event loop" in str(e).lower():
                print(f"⚠️ Event loop conflict, yeni thread'de çalıştırılıyor")
                import threading
                result = [False]
                def run_in_thread():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result[0] = loop.run_until_complete(self._send_async_message(message))
                    finally:
                        loop.close()
                t = threading.Thread(target=run_in_thread)
                t.start()
                t.join(timeout=30)
                return result[0]
            print(f"❌ Telegram mesaj hatası: {e}")
            return False
        except Exception as e:
            print(f"❌ Telegram mesaj hatası: {e}")
            return False

    def format_vulnerability_report(self, results: Dict) -> str:
        """Zafiyet raporunu Telegram mesajı olarak ÇOK DETAYLI formatla"""

        slug = results.get("plugin_slug", "")
        version = results.get("plugin_version", "")
        download_url = f"https://downloads.wordpress.org/plugin/{slug}.{version}.zip" if slug and version else "N/A"

        if not results.get("vulnerabilities_found"):
            message = (
                "🔍 <b>WordPress Plugin Taraması</b>\n\n"
                f"📦 <b>Plugin:</b> {self._escape(results.get('plugin_name', 'Unknown'))}\n"
                f"📌 <b>Versiyon:</b> {self._escape(version)}\n"
                f"🕐 <b>Tarih:</b> {self._escape(results.get('scan_timestamp', 'N/A'))}\n\n"
                f"✅ <b>Sonuç:</b> Doğrulanabilir Zafiyet Bulunamadı\n"
                f"📊 {results.get('total_files_analyzed', 0)} dosya analiz edildi"
            )
            return message

        summary = results.get("summary", {})

        message = (
            "🚨 <b>KRİTİK ZAFIYET BULUNDU!</b> 🚨\n\n"
            f"📦 <b>Plugin:</b> {self._escape(results.get('plugin_name', 'Unknown'))}\n"
            f"📌 <b>Versiyon:</b> {self._escape(version)}\n"
            f"🔗 <b>İndirme Linki:</b> {download_url}\n"
            f"🕐 <b>Tarih:</b> {self._escape(results.get('scan_timestamp', 'N/A'))}\n\n"
            f"📊 <b>Toplam Doğrulanmış Zafiyet:</b> {summary.get('total_vulnerabilities', 0)}\n"
        )

        if "by_severity" in summary:
            message += "\n<b>Önem Dağılımı:</b>\n"
            for severity, count in summary["by_severity"].items():
                sev_emoji = "🔴" if severity == "Critical" else "🟠" if severity == "High" else "🟡" if severity == "Medium" else "🟢"
                message += f"{sev_emoji} {self._escape(severity)}: {count}\n"

        message += "\n" + "=" * 35 + "\n\n"

        # Her zafiyet için DETAYLI açıklama
        for idx, vuln in enumerate(results.get("vulnerabilities_found", []), 1):
            sev = vuln.get("severity", "High")
            severity_emoji = "🔴" if sev == "Critical" else "🟠" if sev == "High" else "🟡"
            cvss = vuln.get("cvss_score", "N/A")
            wf_cat = self._escape(vuln.get("wordfence_category", "Wordfence Verified Exploit"))
            location = self._escape(vuln.get("location", vuln.get("file", "N/A")))
            vuln_type = self._escape(vuln.get("type", "Unknown"))

            # Kod parçası: HTML tag'larını escape et, çok uzunsa kırp
            vulnerable_code = self._escape(str(vuln.get("vulnerable_code", "Belirtilmemiş")))[:350]
            poc = self._escape(str(vuln.get("poc_command", "N/A")))[:500]
            desc = self._escape(str(vuln.get("description", "Açıklama yok")))
            exploit = self._escape(str(vuln.get("exploit_scenario", "Senaryo yok")))
            rec = self._escape(str(vuln.get("recommendation", "Öneri yok")))

            message += (
                f"<b>{idx}. {vuln_type}</b> {severity_emoji}\n"
                f"🛡️ <b>Wordfence Kategori:</b> {wf_cat}\n"
                f"🔥 <b>CVSS Skor:</b> {cvss} ({sev})\n"
                f"📍 <b>Konum:</b> <code>{location}</code>\n\n"
                f"💻 <b>Zafiyetli Kod Parçası:</b>\n"
                f"<code>{vulnerable_code}</code>\n\n"
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
