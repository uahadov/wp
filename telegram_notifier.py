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
            print(f"❌ Telegram gönderme hatası: {e}")
            return False
    
    def format_vulnerability_report(self, results: Dict) -> str:
        """Zafiyet raporunu Telegram mesajı olarak formatla"""
        
        if not results["vulnerabilities_found"]:
            message = f"""
🔍 <b>WordPress Plugin Taraması</b>

📦 <b>Plugin:</b> {results['plugin_name']}
📌 <b>Versiyon:</b> {results['plugin_version']}
🕐 <b>Tarih:</b> {results['scan_timestamp']}

✅ <b>Sonuç:</b> Zafiyet bulunamadı
📊 {results['total_files_analyzed']} dosya analiz edildi
"""
            return message.strip()
        
        # Zafiyet bulundu!
        summary = results["summary"]
        
        message = f"""
🚨 <b>ZAFIYET BULUNDU!</b> 🚨

📦 <b>Plugin:</b> {results['plugin_name']}
📌 <b>Versiyon:</b> {results['plugin_version']}
🕐 <b>Tarih:</b> {results['scan_timestamp']}

📊 <b>Özet:</b>
• Toplam Zafiyet: {summary['total_vulnerabilities']}
"""
        
        # Severity bilgisi
        if "by_severity" in summary:
            message += "\n<b>Önem Dağılımı:</b>\n"
            for severity, count in summary["by_severity"].items():
                emoji = "🔴" if severity == "Critical" else "🟠" if severity == "High" else "🟡" if severity == "Medium" else "🟢"
                message += f"{emoji} {severity}: {count}\n"
        
        message += "\n" + "="*40 + "\n\n"
        
        # Her zafiyet için detay
        for idx, vuln in enumerate(results["vulnerabilities_found"], 1):
            severity_emoji = {
                "Critical": "🔴",
                "High": "🟠",
                "Medium": "🟡",
                "Low": "🟢"
            }.get(vuln["severity"], "⚪")
            
            message += f"""
<b>{idx}. {vuln['type']}</b> {severity_emoji}

<b>Önem:</b> {vuln['severity']} (CVSS: {vuln.get('cvss_score', 'N/A')})
<b>Dosya:</b> {vuln.get('file', vuln.get('location', 'N/A'))}
<b>Açıklama:</b> {vuln['description'][:200]}...

<b>Exploit Senaryosu:</b>
{vuln.get('exploit_scenario', 'Belirtilmemiş')[:300]}...

<b>Çözüm Önerisi:</b>
{vuln.get('recommendation', 'Belirtilmemiş')[:200]}...

{'-'*40}
"""
        
        # CVE başvuru bilgisi
        message += f"""

<b>📌 Sonraki Adımlar:</b>
1. Plugin geliştiricisine özel olarak bildir
2. 90 gün bekle (Responsible Disclosure)
3. CVE başvurusu yap: https://cveform.mitre.org/

<b>⚠️ ÖNEMLİ:</b> Bu bilgileri sorumlu bir şekilde kullanın!
"""
        
        return message.strip()
    
    def send_vulnerability_report(self, results: Dict):
        """Zafiyet raporunu gönder"""
        message = self.format_vulnerability_report(results)
        
        # Asyncio event loop kullan
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        success = loop.run_until_complete(self.send_message(message))
        
        if success:
            print("✅ Telegram bildirimi gönderildi")
        else:
            print("❌ Telegram bildirimi gönderilemedi")
        
        return success
    
    def send_scan_start(self, plugin_count: int):
        """Tarama başlangıç bildirimi"""
        message = f"""
🔄 <b>WordPress Zafiyet Taraması Başladı</b>

📦 {plugin_count} plugin analiz edilecek
⏱️ Tahmini süre: {plugin_count * 2} dakika

Bulgular için beklemede...
"""
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(self.send_message(message.strip()))
    
    def send_scan_complete(self, total_plugins: int, vulns_found: int):
        """Tarama tamamlanma bildirimi"""
        message = f"""
✅ <b>Tarama Tamamlandı</b>

📦 Analiz edilen plugin: {total_plugins}
🚨 Zafiyet bulunan plugin: {vulns_found}

{"🎉 Başarılar!" if vulns_found > 0 else "Sonraki taramaya hazır."}
"""
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(self.send_message(message.strip()))
