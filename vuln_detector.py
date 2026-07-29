"""
AI destekli zafiyet tespit modülü
GitHub AI Models kullanarak derin analiz yapar
"""

import json
import time
from typing import List, Dict, Optional
from openai import OpenAI
import config


class VulnerabilityDetector:
    def __init__(self):
        # GitHub AI Models için OpenAI client kullan
        self.client = OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=config.GITHUB_TOKEN,
        )
        self.model = config.GITHUB_MODEL
    
    def analyze_code_with_ai(self, code_snippet: str, file_path: str) -> Optional[Dict]:
        """AI ile kod analizi yap"""
        try:
            print(f"🤖 AI analizi: {file_path}")
            
            # Kod çok uzunsa kısalt (token limiti için)
            if len(code_snippet) > 4000:
                code_snippet = code_snippet[:4000] + "\n... (kod kırpıldı) ..."
            
            prompt = config.ANALYSIS_PROMPT.format(code=code_snippet)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Sen bir WordPress güvenlik uzmanısın. Kod analizi yapıyorsun."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Daha deterministik sonuçlar için
                max_tokens=2000,
            )
            
            result_text = response.choices[0].message.content
            
            # JSON yanıtı parse et
            try:
                # Markdown kod bloğu içindeyse temizle
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0]
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0]
                
                # JSON parse et
                result = json.loads(result_text.strip())
                return result
                
            except json.JSONDecodeError as je:
                # JSON parse hatası - zafiyet yok kabul et
                print(f"⚠️  JSON parse hatası - zafiyet yok kabul edildi")
                return {
                    "vulnerable": False,
                    "vulnerabilities": []
                }
            except Exception as parse_error:
                print(f"⚠️  Parse hatası - zafiyet yok kabul edildi")
                return {
                    "vulnerable": False,
                    "vulnerabilities": []
                }
                
        except Exception as e:
            err_type = type(e).__name__
            err_msg = str(e)
            # Rate limit hatası
            if "429" in err_msg or "rate" in err_msg.lower():
                print(f"⚠️  AI Rate Limit - 10 saniye bekleniyor...")
                import time
                time.sleep(10)
            elif "401" in err_msg or "unauthorized" in err_msg.lower():
                print(f"❌ AI Auth Hatası - GitHub Token geçersiz: {err_msg[:100]}")
            elif "timeout" in err_msg.lower() or "connection" in err_msg.lower():
                print(f"❌ AI Bağlantı Hatası: {err_msg[:100]}")
            else:
                print(f"❌ AI API Hatası ({err_type}): {err_msg[:150]}")
            return {
                "vulnerable": False,
                "vulnerabilities": []
            }
    
    def deep_analyze(self, plugin_info: Dict, suspicious_files: List[Dict]) -> Dict:
        """Şüpheli dosyaları derin analiz et"""
        results = {
            "plugin_name": plugin_info["name"],
            "plugin_version": plugin_info["version"],
            "plugin_slug": plugin_info["slug"],
            "scan_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files_analyzed": len(suspicious_files),
            "vulnerabilities_found": [],
            "summary": {}
        }
        
        print(f"\n🔍 Derin analiz başlıyor: {plugin_info['name']}")
        print(f"📁 {len(suspicious_files)} dosya analiz edilecek\n")
        
        for idx, file_info in enumerate(suspicious_files, 1):
            print(f"[{idx}/{len(suspicious_files)}] Analiz ediliyor: {file_info['path']}")
            
            # AI ile analiz
            ai_result = self.analyze_code_with_ai(
                file_info["content"],
                file_info["path"]
            )
            
            if ai_result and ai_result.get("vulnerable"):
                for vuln in ai_result.get("vulnerabilities", []):
                    vuln["file"] = file_info["path"]
                    results["vulnerabilities_found"].append(vuln)
                    
                    print(f"  🚨 {vuln['severity']} - {vuln['type']}")
            
            # Rate limiting için kısa bekleme
            time.sleep(1)
        
        # Özet oluştur
        if results["vulnerabilities_found"]:
            severity_count = {}
            type_count = {}
            
            for vuln in results["vulnerabilities_found"]:
                severity = vuln["severity"]
                vuln_type = vuln["type"]
                
                severity_count[severity] = severity_count.get(severity, 0) + 1
                type_count[vuln_type] = type_count.get(vuln_type, 0) + 1
            
            results["summary"] = {
                "by_severity": severity_count,
                "by_type": type_count,
                "total_vulnerabilities": len(results["vulnerabilities_found"])
            }
        
        return results
    
    def verify_vulnerability(self, vulnerability: Dict) -> bool:
        """Zafiyetin gerçek ve istismar edilebilir olup olmadığını sıkı kurallarla doğrula"""
        severity = vulnerability.get("severity", "Low")
        cvss_score = float(vulnerability.get("cvss_score", 0))
        vuln_code = vulnerability.get("vulnerable_code", "")
        desc = vulnerability.get("description", "").lower()
        exploit = vulnerability.get("exploit_scenario", "").lower()

        # 1.uninstall veya kaldırma dosyası ise reddet
        loc = vulnerability.get("location", "").lower()
        if "uninstall" in loc or "uninstall.php" in desc:
            return False

        # 2. Zafiyetli kod parçası boşsa reddet
        if not vuln_code or len(vuln_code.strip()) < 5:
            return False

        # 3. CVSS skoru 7.0 ve üzeri olmalı
        if cvss_score < 7.0:
            return False

        # 4. Kod içerisinde kullanıcı girdisi var mı kontrol et
        user_inputs = ["$_get", "$_post", "$_request", "$_cookie", "$_files", "php://input"]
        code_has_input = any(inp in vuln_code.lower() for inp in user_inputs)
        desc_has_input = any(inp in desc for inp in user_inputs) or "user input" in desc or "unsanitized" in desc

        if not (code_has_input or desc_has_input):
            return False

        return True
    
    def filter_high_confidence_vulns(self, results: Dict) -> Dict:
        """Sadece yüksek güvenirlikli zafiyetleri filtrele"""
        verified_vulns = []
        
        for vuln in results["vulnerabilities_found"]:
            if self.verify_vulnerability(vuln):
                verified_vulns.append(vuln)
        
        results["vulnerabilities_found"] = verified_vulns
        
        # Özeti güncelle
        if verified_vulns:
            severity_count = {}
            type_count = {}
            
            for vuln in verified_vulns:
                severity = vuln["severity"]
                vuln_type = vuln["type"]
                
                severity_count[severity] = severity_count.get(severity, 0) + 1
                type_count[vuln_type] = type_count.get(vuln_type, 0) + 1
            
            results["summary"] = {
                "by_severity": severity_count,
                "by_type": type_count,
                "total_vulnerabilities": len(verified_vulns)
            }
        else:
            results["summary"] = {
                "total_vulnerabilities": 0
            }
        
        return results
