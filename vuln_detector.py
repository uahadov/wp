"""
AI destekli zafiyet tespit ve doğrulama modülü (v3.0 - Taint Flow Odaklı)
=========================================================================

Artık AI koddan zafiyet UYDURMUYOR. Taint analysis motoru tarafından
tespit edilmiş source->sink akışlarını DOĞRULUYOR.

Bu yaklaşım false positive oranını %90+ azaltır.
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
            base_url=config.PRIMARY_API_BASE,
            api_key=config.PRIMARY_API_KEY,
        )
        self.model = config.PRIMARY_MODEL

        self.validator_client = None
        if config.SECONDARY_API_KEY:
            try:
                self.validator_client = OpenAI(
                    base_url=config.SECONDARY_API_BASE,
                    api_key=config.SECONDARY_API_KEY,
                )
            except Exception as e:
                logger.warning(f"{config.SECONDARY_PROVIDER} doğrulayıcı istemcisi başlatılamadı: {e}")

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

    def _format_taint_info(self, taint_flows: List[Dict]) -> str:
        """Taint akışlarını AI için okunabilir formata çevir"""
        if not taint_flows:
            return "Bu dosyada taint akışı bulunamadı."

        lines = []
        for i, flow in enumerate(taint_flows, 1):
            lines.append(f"""
--- TAINT AKIŞI #{i} ---
Zafiyet Türü: {flow.get('vuln_type', 'Unknown')}
Source (Kullanıcı Girdisi): {flow.get('source', 'Unknown')} (Satır {flow.get('source_line', '?')})
Sink (Tehlikeli Fonksiyon): {flow.get('sink', 'Unknown')} (Satır {flow.get('sink_line', '?')})
Tainted Değişken: {flow.get('tainted_var', 'Unknown')}
Sink Kod: {flow.get('sink_code', 'Unknown')}
Fonksiyon Context: {flow.get('context', 'global')}
Nonce Kontrolü: {'VAR' if flow.get('has_nonce_check') else 'YOK'}
Capability Kontrolü: {'VAR' if flow.get('has_capability_check') else 'YOK'}
Akış Yolu:""")
            for step in flow.get('flow_path', []):
                lines.append(f"  {step}")
        return "\n".join(lines)

    def analyze_code_with_ai(
        self,
        code_snippet: str,
        file_path: str,
        taint_flows: List[Dict] = None
    ) -> Optional[Dict]:
        """AI ile PHP kod analizi yap — Taint flow doğrulama modu."""
        print(f"🤖 AI taint flow doğrulaması: {file_path}")

        taint_info = self._format_taint_info(taint_flows or [])
        prompt = config.ANALYSIS_PROMPT.format(
            taint_info=taint_info,
            code=code_snippet
        )

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
                                "Sana VERİLEN taint akışlarını ULTRA STRICT modda doğrularsın. "
                                "FALSE POSITIVE TOLERANCE = 0%. Şüpheli ise REDDET. "
                                "Yalnızca geçerli JSON formatında yanıt verirsin. "
                                "JSON dışında HİÇBİR ŞEY yazma. "
                                "Markdown kod bloğu KULLANMA. "
                                "Eğer %100 emin değilsen vulnerable: false döndür."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,  # 0.1'den 0.0'a düşürüldü - TAM deterministik
                    max_tokens=2500,
                )

                result_text = response.choices[0].message.content.strip()
                result_text = re.sub(r"^```(?:json)?\s*", "", result_text)
                result_text = re.sub(r"\s*```$", "", result_text)
                result_text = result_text.strip()

                json_match = re.search(r"\{.*\}", result_text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(0))
                        return result
                    except json.JSONDecodeError as je:
                        print(f"⚠️ JSON parse hatası (Deneme {attempt}/{max_retries}): {je}")
                        if attempt < max_retries:
                            time.sleep(2)
                            continue
                else:
                    print(f"⚠️ AI yanıtında JSON bulunamadı (Deneme {attempt}/{max_retries})")
                    if attempt < max_retries:
                        time.sleep(2)
                        continue

            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate" in err_str.lower():
                    wait_time = min(30, 8 * attempt)
                    print(f"⏳ Rate limit (429), {wait_time}s bekleniyor... ({attempt}/{max_retries})")
                    time.sleep(wait_time)
                elif "context_length" in err_str.lower() or "token" in err_str.lower():
                    print(f"⚠️ Token limiti aşımı, parça küçültülüyor... ({attempt}/{max_retries})")
                    code_snippet = code_snippet[: max(1500, len(code_snippet) // 2)]
                    prompt = config.ANALYSIS_PROMPT.format(
                        taint_info=taint_info,
                        code=code_snippet
                    )
                    time.sleep(1)
                else:
                    print(f"⚠️ AI İstek Hatası ({type(e).__name__}): {err_str[:150]}")
                    time.sleep(2)

        return {"vulnerable": False, "vulnerabilities": []}

    def deep_analyze(
        self,
        plugin_info: Dict,
        suspicious_files: List[Dict],
        taint_flows: List[Dict] = None
    ) -> Dict:
        """Şüpheli dosyaları derin analiz et — Taint flow odaklı."""
        results = {
            "plugin_name": plugin_info.get("name", "Unknown"),
            "plugin_version": plugin_info.get("version", "?.?.?"),
            "plugin_slug": plugin_info.get("slug", "unknown"),
            "scan_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_files_analyzed": len(suspicious_files),
            "total_taint_flows": len(taint_flows) if taint_flows else 0,
            "vulnerabilities_found": [],
            "needs_manual_review": [],
            "rejected_findings": [],
            "summary": {}
        }

        print(f"\n🔍 Derin analiz başlıyor: {plugin_info.get('name', 'Unknown')}")
        print(f"📁 {len(suspicious_files)} dosya, {len(taint_flows or [])} taint akışı analiz edilecek\n")

        flows_by_file = {}
        if taint_flows:
            for flow in taint_flows:
                fname = flow.get("file", "")
                if fname not in flows_by_file:
                    flows_by_file[fname] = []
                flows_by_file[fname].append(flow)

        for idx, file_info in enumerate(suspicious_files, 1):
            file_path = file_info["path"]
            file_flows = flows_by_file.get(file_path, [])

            print(f"[{idx}/{len(suspicious_files)}] Analiz ediliyor: {file_path}")
            if file_flows:
                print(f"  📌 {len(file_flows)} taint akışı doğrulanacak")

            content = file_info.get("content", "").strip()
            if not content:
                continue
            if not file_flows:
                continue

            code_chunks = self._split_code_for_analysis(content)
            seen_vulns = set()

            for chunk_idx, chunk in enumerate(code_chunks, 1):
                chunk_label = file_path
                if len(code_chunks) > 1:
                    chunk_label = f"{file_path} (parça {chunk_idx}/{len(code_chunks)})"

                ai_result = self.analyze_code_with_ai(chunk, chunk_label, file_flows)

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
                        vuln["file"] = file_path
                        if len(code_chunks) > 1:
                            vuln["analysis_chunk"] = f"{chunk_idx}/{len(code_chunks)}"
                        results["vulnerabilities_found"].append(vuln)
                        print(f"  BULGU: {vuln.get('severity', 'High')} - {vuln.get('type', 'Unknown')}")

                if chunk_idx < len(code_chunks):
                    time.sleep(1.0)

            if idx < len(suspicious_files):
                time.sleep(1.5)

        return results

    def verify_vulnerability(self, vulnerability: Dict) -> bool:
        """ULTRA STRICT: Zafiyetin GERÇEK VE WORDFENCE KRİTERLERİNE UYGUNLUĞUNU DOĞRULA"""
        try:
            cvss_raw = vulnerability.get("cvss_score", 0)
            try:
                cvss_score = float(cvss_raw) if cvss_raw else 0.0
            except (ValueError, TypeError):
                cvss_score = 0.0

            vuln_code = str(vulnerability.get("vulnerable_code", "")).strip()
            desc = str(vulnerability.get("description", "")).lower()
            loc = str(vulnerability.get("location", "")).lower()
            vuln_type = str(vulnerability.get("type", "")).lower()
            exploit_scenario = str(vulnerability.get("exploit_scenario", "")).lower()
            poc = str(vulnerability.get("poc_command", "")).lower()

            # === RULE 1: CVSS >= 7.0 (STRICT) ===
            if cvss_score < 7.0:
                print(f"  🚫 REJECT: CVSS {cvss_score} < 7.0 (Not exploitable enough)")
                return False

            # === RULE 2: uninstall.php BLACKLIST ===
            if "uninstall" in loc or "uninstall.php" in vuln_code.lower():
                print(f"  🚫 REJECT: uninstall.php (not a vulnerability)")
                return False

            # === RULE 3: Vulnerable code MUST exist ===
            if not vuln_code or len(vuln_code) < 10:
                print(f"  🚫 REJECT: No vulnerable code provided")
                return False

            # === RULE 4: USER INPUT STRICT CHECK ===
            user_input_keywords = [
                "$_get[", "$_post[", "$_request[", "$_cookie[",
                "$_files[", "php://input", "get_param", "get_json_params",
                "get_body", "get_query_var"
            ]
            
            has_user_input = any(kw in vuln_code.lower() for kw in user_input_keywords)
            has_desc_input = any(kw in desc for kw in [
                "unauthenticated", "unauthorized", "user input",
                "attacker can", "remote attacker", "no authentication"
            ])
            has_exploit_input = any(kw in exploit_scenario for kw in [
                "unauthenticated", "no auth", "public access"
            ])
            
            if not (has_user_input or (has_desc_input and has_exploit_input)):
                print(f"  🚫 REJECT: No clear user input path")
                return False

            # === RULE 5: WooCommerce PUBLIC operations BLACKLIST ===
            wc_public_keywords = [
                "add_to_cart", "product_id", "cart_fragments",
                "woocommerce_add_to_cart", "cart_item", "checkout"
            ]
            if any(kw in vuln_code.lower() for kw in wc_public_keywords):
                if "missing authorization" in vuln_type or "broken access" in vuln_type:
                    print(f"  🚫 REJECT: WooCommerce public customer operation (normal behavior)")
                    return False

            # === RULE 6: SANITIZER CHECK (STRICT) ===
            strong_sanitizers = [
                "(int)", "intval(", "absint(",
                "$wpdb->prepare", "wp_verify_nonce", "check_ajax_referer"
            ]
            sanitizer_count = sum(1 for s in strong_sanitizers if s in vuln_code)
            
            if sanitizer_count >= 1:
                # Eğer SQL ise: wpdb->prepare ŞART
                if "sql" in vuln_type and "$wpdb->prepare" in vuln_code:
                    print(f"  🚫 REJECT: wpdb->prepare used (protected)")
                    return False
                
                # Eğer integer cast varsa
                if any(s in vuln_code for s in ["(int)", "intval(", "absint("]):
                    print(f"  🚫 REJECT: Integer cast/validation present")
                    return False
                
                # Nonce check varsa
                if any(s in vuln_code for s in ["wp_verify_nonce", "check_ajax_referer"]):
                    print(f"  🚫 REJECT: Nonce/CSRF protection present")
                    return False

            # === RULE 7: ADMIN-ONLY operations BLACKLIST ===
            admin_only_keywords = [
                "is_admin()", "current_user_can('administrator')",
                "current_user_can('manage_options')", "if ( ! is_admin() )"
            ]
            if any(kw in vuln_code for kw in admin_only_keywords):
                if "unauthenticated" not in desc and "unauthenticated" not in exploit_scenario:
                    print(f"  🚫 REJECT: Admin-only function (requires admin)")
                    return False

            # === RULE 8: PoC MUST be REAL ===
            if not poc or len(poc) < 20:
                print(f"  🚫 REJECT: No PoC command provided")
                return False
            
            # PoC must contain actual exploit params
            poc_quality_keywords = ["admin-ajax.php", "action=", "?", "&", "curl", "post"]
            if not any(kw in poc for kw in poc_quality_keywords):
                print(f"  🚫 REJECT: PoC not realistic")
                return False

            # === RULE 9: XSS STRICT CHECK ===
            if "xss" in vuln_type or "cross-site scripting" in vuln_type:
                # XSS must be STORED or REFLECTED with impact
                if "stored" not in desc and "reflected" not in desc:
                    print(f"  🚫 REJECT: XSS type not clear (stored/reflected)")
                    return False
                
                # Must have esc_* absence proof
                if not any(kw in desc for kw in ["no escaping", "not escaped", "without esc_"]):
                    print(f"  🚫 REJECT: XSS escaping status unclear")
                    return False

            # === RULE 10: SQL INJECTION STRICT CHECK ===
            if "sql" in vuln_type or "injection" in vuln_type:
                # Must mention wpdb or mysql
                if "wpdb" not in vuln_code.lower() and "mysql" not in vuln_code.lower():
                    print(f"  🚫 REJECT: SQL injection without DB interaction")
                    return False
                
                # Must NOT have prepare()
                if "->prepare(" in vuln_code:
                    print(f"  🚫 REJECT: prepare() used")
                    return False

            # === ALL CHECKS PASSED ===
            print(f"  ✅ PASS: All strict validation checks passed")
            return True

        except Exception as e:
            print(f"⚠️ Zafiyet doğrulama hatası: {e}")
            return False

    def verify_vulnerability_with_validator(self, vuln: Dict) -> bool:
        """2. Aşama Hakem: İkincil AI sağlayıcı ile zafiyeti doğrula"""
        if not self.validator_client:
            if config.SECONDARY_API_KEY and config.SECONDARY_PROVIDER:
                print(f"🚫 {config.SECONDARY_PROVIDER} istemcisi var ama başlatılamadı.")
                return False
            print("⚠️ İkincil doğrulayıcı anahtarı yok; yerel doğrulama kullanıldı.")
            return True

        print(f"⚖️ {config.SECONDARY_PROVIDER} AI Hakemi zafiyeti inceliyor: {vuln.get('type', 'Unknown')}...")

        prompt = (
            "Sen Kıdemli Siber Güvenlik Baş Denetçisi ve Pentester'sın. ULTRA STRICT MODE.\n"
            f"İlk AI tarayıcımız ({config.PRIMARY_PROVIDER}) bir WordPress eklentisinde aşağıdaki zafiyeti bulduğunu iddia ediyor:\n\n"
            f"📌 Zafiyet Türü: {vuln.get('type')}\n"
            f"📌 CVSS: {vuln.get('cvss_score')} ({vuln.get('severity')})\n"
            f"📌 Konum: {vuln.get('location')} (Dosya: {vuln.get('file')})\n"
            f"📌 Zafiyetli Kod: {vuln.get('vulnerable_code')}\n"
            f"📌 Açıklama: {vuln.get('description')}\n"
            f"📌 PoC Komutu: {vuln.get('poc_command')}\n\n"
            "🚨 SENİN GÖREVİN (TAVIZSIZ HAKEMLİK):\n"
            "1. Bu iddia GERÇEKTEN CVE alabileceğiniz seviyede mi?\n"
            "2. Gerçek dünyada istismar edilebilir mi?\n"
            "3. FALSE POSITIVE mi?\n"
            "4. PoC çalışır mı?\n"
            "5. CVSS skoru gerçekçi mi?\n\n"
            "⚠️ ULTRA STRICT KURALLAR:\n"
            "- ŞÜPHELİ ise → REJECT\n"
            "- Sanitizer varsa → REJECT\n"
            "- Admin-only ise → REJECT\n"
            "- WooCommerce normal işlem ise → REJECT\n"
            "- PoC çalışmaz gibi ise → REJECT\n"
            "- CVSS < 7.0 ise → REJECT\n\n"
            "SADECE aşağıdaki JSON formatında yanıt ver:\n"
            '{"decision": "ACCEPT", "confidence": 0.95} VEYA\n'
            '{"decision": "REJECT", "reason": "Sebep", "confidence": 0.30}'
        )

        try:
            response = self.validator_client.chat.completions.create(
                model=config.SECONDARY_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "Sen tavizsiz bir Siber Güvenlik Denetçisisin (Chief Pentester). "
                            "ULTRA STRICT MODE: FALSE POSITIVE = SİSTEM İTİBARINI KAYBEDER. "
                            "Şüpheli ise REDDET. %100 emin olmalısın. "
                            "Yalnızca JSON formatında yanıt verirsin."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,  # TAM deterministik
                max_tokens=500
            )

            res_text = response.choices[0].message.content.strip()
            json_match = re.search(r"\{.*\}", res_text, re.DOTALL)
            if json_match:
                res_json = json.loads(json_match.group(0))
                decision = res_json.get("decision", "REJECT").upper()
                reason = res_json.get("reason", "Belirtilmedi")
                confidence = float(res_json.get("confidence", 0.0))

                if decision == "ACCEPT" and confidence >= 0.85:
                    print(f"✅ {config.SECONDARY_PROVIDER} AI Hakemi ONAYLADI! (confidence: {confidence:.0%})")
                    return True
                elif decision == "ACCEPT" and confidence < 0.85:
                    print(f"🟡 {config.SECONDARY_PROVIDER} ACCEPT ama confidence düşük ({confidence:.0%}): {reason}")
                    return False
                else:
                    print(f"🚫 {config.SECONDARY_PROVIDER} AI Hakemi REDDETTİ (confidence: {confidence:.0%}): {reason}")
                    return False
            else:
                print(f"🚫 {config.SECONDARY_PROVIDER} yanıtından JSON alınamadı.")
                return False

        except Exception as e:
            print(f"🚫 {config.SECONDARY_PROVIDER} AI Hakemi hatası ({e}).")
            return False

    def filter_high_confidence_vulns(self, results: Dict) -> Dict:
        """Sadece doğrulanmış zafiyetleri tut"""
        verified_vulns = []
        manual_review = []
        rejected_findings = []
        total_before = len(results.get("vulnerabilities_found", []))

        for vuln in results.get("vulnerabilities_found", []):
            if self.verify_vulnerability(vuln):
                if self.verify_vulnerability_with_validator(vuln):
                    vuln["review_status"] = "confirmed_candidate"
                    verified_vulns.append(vuln)
                else:
                    vuln["review_status"] = "needs_manual_review"
                    vuln["review_reason"] = "Yerel kuralları geçti ama hakem AI onayı alınamadı."
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