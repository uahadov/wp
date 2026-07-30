"""
AI destekli zafiyet tespit ve doğrulama modülü
GitHub AI Models (gpt-4o) kullanır
"""

import re
import json
import time
import logging
from typing import List, Dict, Optional
from openai import OpenAI
import config

logger = logging.getLogger(__name__)


class VulnerabilityDetector:
    def __init__(self):
        self.client = OpenAI(
            base_url=config.GITHUB_API_BASE,
            api_key=config.GITHUB_TOKEN,
        )
        self.model = config.GITHUB_MODEL

        # Secondary AI Validator (Google Gemini 2.5/3.5 Flash)
        self.gemini_client = None
        if config.GEMINI_API_KEY and config.GEMINI_API_KEY != "your_gemini_api_key_here":
            try:
                self.gemini_client = OpenAI(
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    api_key=config.GEMINI_API_KEY,
                )
            except Exception as e:
                logger.warning(f"Gemini API istemcisi başlatılamadı: {e}")

    def _split_code_for_analysis(self, code: str, max_chars: int = 5500, overlap: int = 500) -> List[str]:
        """Büyük dosyaları ortasını kaybetmeden, örtüşen parçalara böl."""
        code = code.strip()
        if len(code) <= max_chars:
            return [code]

        chunks = []
        start = 0
        while start < len(code):
            end = min(start + max_chars, len(code))
            if end < len(code):
                newline_pos = code.rfind("\n", start, end)
                if newline_pos > start + max_chars // 2:
                    end = newline_pos

            chunks.append(code[start:end])
            if end >= len(code):
                break
            start = max(0, end - overlap)

        return chunks

    def _build_evidence_context(self, code: str, file_path: str) -> str:
        """AI'a dosyanın güvenlik sinyallerini kısa ve kanıtlı şekilde ver."""
        checks = {
            "public_ajax": r"add_action\s*\(\s*['\"]wp_ajax_nopriv_([^'\"]+)",
            "ajax": r"add_action\s*\(\s*['\"]wp_ajax_([^'\"]+)",
            "admin_post_public": r"add_action\s*\(\s*['\"]admin_post_nopriv_([^'\"]+)",
            "rest_route": r"register_rest_route\s*\(",
            "shortcode": r"add_shortcode\s*\(",
            "user_input": r"\$_(GET|POST|REQUEST|COOKIE|FILES)|php://input|get_param\s*\(",
            "dangerous_sink": (
                r"\$wpdb->(query|get_results|get_row|get_var)\s*\(|"
                r"file_get_contents\s*\(|file_put_contents\s*\(|unlink\s*\(|"
                r"include(?:_once)?\s*\(|require(?:_once)?\s*\(|"
                r"eval\s*\(|system\s*\(|exec\s*\(|shell_exec\s*\(|"
                r"wp_remote_(get|post)\s*\(|wp_redirect\s*\("
            ),
            "nonce_check": r"wp_verify_nonce\s*\(|check_ajax_referer\s*\(",
            "capability_check": r"current_user_can\s*\(|is_admin\s*\(",
            "sanitizer": r"sanitize_[a-zA-Z0-9_]+\s*\(|esc_(html|attr|url|js)\s*\(|intval\s*\(|absint\s*\(|\$wpdb->prepare\s*\(",
        }

        lines = code.splitlines()

        def sample(pattern: str, limit: int = 6) -> List[str]:
            hits = []
            for line_no, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    clean = line.strip()
                    if len(clean) > 180:
                        clean = clean[:177] + "..."
                    hits.append(f"L{line_no}: {clean}")
                    if len(hits) >= limit:
                        break
            return hits

        found = {name: sample(pattern) for name, pattern in checks.items()}
        risk_score = 0
        if found["public_ajax"] or found["admin_post_public"]:
            risk_score += 35
        if found["rest_route"]:
            risk_score += 25
        if found["user_input"]:
            risk_score += 25
        if found["dangerous_sink"]:
            risk_score += 30
        if not found["nonce_check"]:
            risk_score += 10
        if not found["capability_check"]:
            risk_score += 10
        if found["sanitizer"]:
            risk_score -= 15
        risk_score = max(0, min(100, risk_score))

        sections = [
            "=== OTOMATİK KANIT ÖZETİ ===",
            f"Dosya: {file_path}",
            f"Yerel risk skoru: {risk_score}/100",
        ]
        for label, key in [
            ("Public AJAX", "public_ajax"),
            ("AJAX", "ajax"),
            ("Public admin_post", "admin_post_public"),
            ("REST route", "rest_route"),
            ("Shortcode", "shortcode"),
            ("Kullanıcı girdisi", "user_input"),
            ("Tehlikeli sink", "dangerous_sink"),
            ("Nonce kontrolu", "nonce_check"),
            ("Yetki kontrolu", "capability_check"),
            ("Sanitizer/escape", "sanitizer"),
        ]:
            values = found[key]
            sections.append(f"{label}:")
            sections.extend([f"- {value}" for value in values] if values else ["- Yok"])

        sections.append("=== KOD ===")
        return "\n".join(sections) + "\n" + code

    def analyze_code_with_ai(self, code_snippet: str, file_path: str) -> Optional[Dict]:
        """AI ile PHP kod analizi yap (Otomatik Retry ve Kesin JSON Parse)"""
        print(f"🤖 AI analizi: {file_path}")

        code_snippet = self._build_evidence_context(code_snippet, file_path)
        prompt = config.ANALYSIS_PROMPT.format(code=code_snippet)

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Sen kıdemli bir WordPress Güvenlik Araştırmacısısın (Exploit Developer). "
                                "Yalnızca geçerli JSON formatında yanıt verirsin. "
                                "JSON dışında HİÇBİR ŞEY yazma. "
                                "Markdown kod bloğu (``` veya ```json) KULLANMA."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2500,
                )

                result_text = response.choices[0].message.content.strip()

                # Önce markdown kod bloğunu temizle (```json ... ```)
                result_text = re.sub(r"^```(?:json)?\s*", "", result_text)
                result_text = re.sub(r"\s*```$", "", result_text)
                result_text = result_text.strip()

                # JSON bloğunu çek: en dışta başlayan { ... } bloğunu al
                json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
                if json_match:
                    clean_json_str = json_match.group(0)
                    try:
                        result = json.loads(clean_json_str)
                        return result
                    except json.JSONDecodeError as je:
                        print(f"⚠️ JSON parse hatası (Deneme {attempt}/{max_retries}): {je}")
                        # Hatalı JSON'u yeniden dene
                        if attempt < max_retries:
                            time.sleep(2)
                            continue
                else:
                    print(f"⚠️ AI yanıtında JSON bulunamadı (Deneme {attempt}/{max_retries})")
                    print(f"   AI çıktısı: {result_text[:200]}")
                    if attempt < max_retries:
                        time.sleep(2)
                        continue

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    wait_time = min(30, 8 * attempt)  # Exponential backoff
                    print(f"⏳ Rate limit (429), {wait_time}s bekleniyor... ({attempt}/{max_retries})")
                    time.sleep(wait_time)
                elif "context_length" in err_str.lower() or "token" in err_str.lower():
                    # Token aşımı: kodu daha fazla kırp ve yeniden dene
                    print(f"⚠️ Token limiti aşımı, parça küçültülüyor... ({attempt}/{max_retries})")
                    code_snippet = code_snippet[: max(1500, len(code_snippet) // 2)]
                    prompt = config.ANALYSIS_PROMPT.format(code=code_snippet)
                    time.sleep(1)
                else:
                    print(f"⚠️ AI İstek Hatası ({type(e).__name__}): {err_str[:150]}")
                    time.sleep(2)

        return {"vulnerable": False, "vulnerabilities": []}

    def deep_analyze(self, plugin_info: Dict, suspicious_files: List[Dict]) -> Dict:
        """Şüpheli dosyaları derin analiz et"""
        results = {
            "plugin_name": plugin_info.get("name", "Unknown"),
            "plugin_version": plugin_info.get("version", "?.?.?"),
            "plugin_slug": plugin_info.get("slug", "unknown"),
            "scan_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files_analyzed": len(suspicious_files),
            "vulnerabilities_found": [],
            "needs_manual_review": [],
            "rejected_findings": [],
            "summary": {}
        }

        print(f"\n🔍 Derin analiz başlıyor: {plugin_info.get('name', 'Unknown')}")
        print(f"📁 {len(suspicious_files)} dosya analiz edilecek\n")

        for idx, file_info in enumerate(suspicious_files, 1):
            print(f"[{idx}/{len(suspicious_files)}] Analiz ediliyor: {file_info['path']}")

            # Dosya içeriği boşsa atla
            content = file_info.get("content", "").strip()
            if not content:
                print(f"  ⚠️ Dosya içeriği boş, atlanıyor")
                continue

            code_chunks = self._split_code_for_analysis(content)
            seen_vulns = set()

            for chunk_idx, chunk in enumerate(code_chunks, 1):
                chunk_label = file_info["path"]
                if len(code_chunks) > 1:
                    chunk_label = f"{file_info['path']} (parça {chunk_idx}/{len(code_chunks)})"

                ai_result = self.analyze_code_with_ai(chunk, chunk_label)

                if ai_result and ai_result.get("vulnerable"):
                    for vuln in ai_result.get("vulnerabilities", []):
                        if not isinstance(vuln, dict):
                            continue

                        dedupe_key = (
                            str(vuln.get("type", "")),
                            str(vuln.get("location", "")),
                            str(vuln.get("vulnerable_code", ""))[:200],
                        )
                        if dedupe_key in seen_vulns:
                            continue
                        seen_vulns.add(dedupe_key)

                        vuln["file"] = file_info["path"]
                        if len(code_chunks) > 1:
                            vuln["analysis_chunk"] = f"{chunk_idx}/{len(code_chunks)}"
                        results["vulnerabilities_found"].append(vuln)
                        print(f"  BULGU: {vuln.get('severity', 'High')} - {vuln.get('type', 'Unknown')}")

                if chunk_idx < len(code_chunks):
                    time.sleep(1.0)

            # Her dosya arası rate limit koruması
            if idx < len(suspicious_files):
                time.sleep(1.5)

        return results

    def verify_vulnerability(self, vulnerability: Dict) -> bool:
        """Zafiyetin GERÇEK VE WORDFENCE KRİTERLERİNE UYGUNLUĞUNU SU SIZDIRMAZ ŞEKİLDE DOĞRULA"""
        try:
            cvss_raw = vulnerability.get("cvss_score", 0)
            # cvss_score bazen "9.8" gibi string gelebilir
            try:
                cvss_score = float(cvss_raw) if cvss_raw else 0.0
            except (ValueError, TypeError):
                cvss_score = 0.0

            vuln_code = str(vulnerability.get("vulnerable_code", "")).strip()
            desc = str(vulnerability.get("description", "")).lower()
            loc = str(vulnerability.get("location", "")).lower()
            vuln_type = str(vulnerability.get("type", "")).lower()
            exploit_scenario = str(vulnerability.get("exploit_scenario", "")).lower()

            # 1. uninstall.php veya silme işlemleri KESİNLİKLE REDDEDİLİR
            if "uninstall" in loc or "uninstall.php" in desc or "uninstall.php" in vuln_code.lower():
                print(f"  🚫 Reddedildi: uninstall.php içeriyor")
                return False

            # 2. Zafiyetli kod parçası verilmemişse uydurmadır, REDDET
            if not vuln_code or len(vuln_code) < 5:
                print(f"  🚫 Reddedildi: Zafiyetli kod eksik")
                return False

            # 3. Wordfence Bug Bounty barajı: CVSS skoru en az 7.0 olmalı
            if cvss_score < 7.0:
                print(f"  🚫 Reddedildi: CVSS {cvss_score} < 7.0")
                return False

            # 4. Kodda Dışarıdan Kullanıcı Girdisi Bağı Olmak Zorundadır
            user_inputs = [
                "$_get", "$_post", "$_request", "$_cookie",
                "$_files", "php://input", "rest_base",
                "get_param", "sanitize_", "wp_unslash"
            ]
            has_direct_input = any(inp in vuln_code.lower() for inp in user_inputs)
            has_desc_input = (
                any(inp in desc for inp in ["$_get", "$_post", "$_request"]) or
                "unauthenticated" in desc or
                "user input" in desc or
                "missing authorization" in desc or
                "no authentication" in desc or
                "unauthorized" in desc or
                "unauthenticated" in exploit_scenario or
                "unauthenticated" in vuln_type
            )

            if not (has_direct_input or has_desc_input):
                print(f"  🚫 Reddedildi: Kullanıcı girdisi bağı yok")
                return False

            # 5. WooCommerce Sepet / Müşteri public eylemleri ZAFİYET DEĞİLDİR (Otomatik Reddet)
            public_wc_keywords = ["add_to_cart", "product_id", "cart_fragments", "woocommerce_add_to_cart"]
            if any(kw in vuln_code.lower() for kw in public_wc_keywords) or any(kw in desc for kw in public_wc_keywords):
                if "missing authorization" in vuln_type or "missing authorization" in desc:
                    print(f"  🚫 Reddedildi: WooCommerce standart public müşteri eylemi / product_id kullanımı")
                    return False

            # 6. Type casting (int) veya intval() yapılmış parametreler SQLi / Injection olamaz (Otomatik Reddet)
            if "(int)" in vuln_code or "intval(" in vuln_code or "absint(" in vuln_code:
                if "sql" in vuln_type or "injection" in vuln_type or "rce" in vuln_type:
                    print(f"  🚫 Reddedildi: Parametre (int) / intval() ile güvenli tamsayıya dönüştürülmüş")
                    return False

            # 7. Kodda Temizleme/Koruma Fonksiyonu Varsa REDDET (False Positive Koruması)
            full_sanitizers = [
                "sanitize_text_field", "esc_html", "esc_attr",
                "intval(", "(int)", "absint(",
                "wp_verify_nonce", "check_ajax_referer"
            ]
            
            # Nonce veya ajax referer kontrolü açıklama veya kodda varsa reddet
            if "wp_verify_nonce" in vuln_code or "check_ajax_referer" in vuln_code:
                print(f"  🚫 Reddedildi: Nonce / Referer kontrolü mevcut")
                return False

            # Sadece tam korumayı reddet
            if all(san in vuln_code for san in ["$wpdb->prepare"]) and not any(
                bypass in vuln_code.lower() for bypass in ["$_get", "$_post", "$_request", "$_cookie"]
            ):
                print(f"  🚫 Reddedildi: wpdb->prepare ile koruma var ve kullanıcı girdisi yoktur")
                return False

            # Tüm sanitizer'lar bir arada varsa (birden fazla savunma katmanı) reddet
            sanitizer_count = sum(1 for s in full_sanitizers if s in vuln_code)
            if sanitizer_count >= 2:
                print(f"  🚫 Reddedildi: {sanitizer_count} sanitizer/escape fonksiyonu var")
                return False

            return True

        except Exception as e:
            print(f"⚠️ Zafiyet doğrulama hatası: {e}")
            return False

    def verify_vulnerability_with_gemini(self, vuln: Dict) -> bool:
        """2. Aşama Hakem: Google Gemini 2.5/3.5 Flash ile zafiyeti sert bir Pentester gözüyle doğrula"""
        if not self.gemini_client:
            if config.GEMINI_API_KEY and config.GEMINI_API_KEY != "your_gemini_api_key_here":
                print("🚫 Gemini API anahtarı var ama istemci başlatılamadı; zafiyet onaylanmadı.")
                return False
            print("⚠️ Gemini API anahtarı yok; yalnızca yerel doğrulama kuralları kullanıldı.")
            return True

        print(f"⚖️ Gemini AI Hakemi zafiyeti inceliyor: {vuln.get('type', 'Unknown')}...")

        prompt = (
            "Sen Kıdemli Siber Güvenlik Baş Denetçisi ve Pentester'sın.\n"
            "İlk AI tarayıcımız (GPT-4o) bir WordPress eklentisinde aşağıdaki zafiyeti bulduğunu iddia ediyor:\n\n"
            f"📌 Zafiyet Türü: {vuln.get('type')}\n"
            f"📌 Konum: {vuln.get('location')} (Dosya: {vuln.get('file')})\n"
            f"📌 Zafiyetli Kod: {vuln.get('vulnerable_code')}\n"
            f"📌 Açıklama: {vuln.get('description')}\n"
            f"📌 PoC Komutu: {vuln.get('poc_command')}\n\n"
            "GÖREVİN VE DEĞERLENDİRME KRİTERLERİN:\n"
            "1. Bu iddia GERÇEK, dışarıdan istismar edilebilir ve CVE / Bug Bounty almaya değer su sızdırmaz bir zafiyet midir?\n"
            "2. Yoksa bu bir False Positive mi? (Örn: Zaten herkese açık e-ticaret/sepet verisi, sadece Admin yetkili zararsız dosya yükleme, tam sanitization/nonce olan kod, saçma/değersiz iddia).\n"
            "3. Eğer zafiyet değersiz, saçma veya False Positive ise KESİNLİKLE 'REJECT' ver.\n\n"
            "SADECE aşağıdaki JSON formatında yanıt ver:\n"
            '{"decision": "ACCEPT"} veya {"decision": "REJECT", "reason": "Reddetme sebebi"}'
        )

        try:
            response = self.gemini_client.chat.completions.create(
                model=config.GEMINI_MODEL,
                messages=[
                    {"role": "system", "content": "Sen tavizsiz bir Siber Güvenlik Denetçisisin. Yalnızca JSON formatında yanıt verirsin."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )

            res_text = response.choices[0].message.content.strip()
            json_match = re.search(r"\{.*\}", res_text, re.DOTALL)
            if json_match:
                res_json = json.loads(json_match.group(0))
                decision = res_json.get("decision", "REJECT").upper()
                reason = res_json.get("reason", "Belirtilmedi")

                if decision == "ACCEPT":
                    print("✅ Gemini AI Hakemi ONAYLADI! (Gerçek CVE adayı)")
                    return True
                else:
                    print(f"🚫 Gemini AI Hakemi REDDETTİ (False Positive): {reason}")
                    return False
            else:
                print("🚫 Gemini yanıtından JSON alınamadı; zafiyet onaylanmadı.")
                return False

        except Exception as e:
            print(f"🚫 Gemini AI Hakemi doğrulama hatası ({e}); zafiyet onaylanmadı.")
            return False

    def filter_high_confidence_vulns(self, results: Dict) -> Dict:
        """Sadece su sızdırmaz doğrulanmış zafiyetleri tut"""
        verified_vulns = []
        manual_review = []
        rejected_findings = []
        total_before = len(results.get("vulnerabilities_found", []))

        for vuln in results.get("vulnerabilities_found", []):
            # 1. Aşama: Python filtreleri & Kurallar
            if self.verify_vulnerability(vuln):
                # 2. Aşama: Google Gemini AI Hakem Doğrulaması
                if self.verify_vulnerability_with_gemini(vuln):
                    vuln["review_status"] = "confirmed_candidate"
                    verified_vulns.append(vuln)
                else:
                    vuln["review_status"] = "needs_manual_review"
                    vuln["review_reason"] = "Yerel kuralları geçti ama Gemini onayı alınamadı."
                    manual_review.append(vuln)
            else:
                vuln["review_status"] = "rejected"
                rejected_findings.append(vuln)

        filtered_count = total_before - len(verified_vulns) - len(manual_review)
        if filtered_count > 0:
            print(f"🔎 {filtered_count} False Positive filtrelendi. {len(verified_vulns)} onaylı aday kaldı.")
        if manual_review:
            print(f"🟡 {len(manual_review)} bulgu manuel incelemeye ayrıldı.")

        results["vulnerabilities_found"] = verified_vulns
        results["needs_manual_review"] = manual_review
        results["rejected_findings"] = rejected_findings

        if verified_vulns:
            severity_count = {}
            type_count = {}
            for vuln in verified_vulns:
                sev = vuln.get("severity", "High")
                v_type = vuln.get("type", "Security Finding")
                severity_count[sev] = severity_count.get(sev, 0) + 1
                type_count[v_type] = type_count.get(v_type, 0) + 1

            results["summary"] = {
                "by_severity": severity_count,
                "by_type": type_count,
                "total_vulnerabilities": len(verified_vulns),
                "needs_manual_review": len(manual_review),
                "rejected_findings": len(rejected_findings)
            }
        else:
            results["summary"] = {
                "total_vulnerabilities": 0,
                "needs_manual_review": len(manual_review),
                "rejected_findings": len(rejected_findings)
            }

        return results
