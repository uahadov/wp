"""
CVE Matcher — Bilinen zafiyet (NVD) eşleştirme modülü
=====================================================

WordPress eklentisi adını NVD'de (National Vulnerability Database) arar,
sürümünü çıkarır ve CVE kaydındaki etkilenen sürüm aralıklarıyla eşleştirir.
Ayrıca her eşleşme için manuel PoC geliştirmeye yardımcı bir Markdown şablonu
üretir (PoC'yi sen manuel yazarsın).

Kullanım:
    python cve_matcher.py --slug <plugin_slug> [--version 1.2.3]
    python cve_matcher.py --cve CVE-2023-1234
    python cve_matcher.py --plugin-path work/<slug>
"""

import sys
import re
import argparse
import config
from pathlib import Path
from typing import Dict, List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import requests
except ImportError:
    print("❌ 'requests' paketi gerekli: pip install requests")
    sys.exit(1)


def _print(text: str = "", code: str = ""):
    codes = {"r": "\033[31m", "g": "\033[32m", "y": "\033[33m",
             "b": "\033[34m", "m": "\033[35m", "c": "\033[36m",
             "bold": "\033[1m", "dim": "\033[2m", "reset": "\033[0m"}
    if code and sys.platform != "win32":
        text = f"{codes.get(code, '')}{text}{codes['reset']}"
    print(text)


class CVEMatcher:
    def __init__(self):
        self.api = config.NVD_API
        self.headers = {"User-Agent": "WP-Vuln-CVE-Matcher/1.0 (Security Research)"}
        if config.NVD_API_KEY:
            self.headers["apiKey"] = config.NVD_API_KEY

    # ----------------------------------------------------------
    # 1) Sürüm çıkarma
    # ----------------------------------------------------------
    def extract_version_from_plugin(self, plugin_path) -> Optional[str]:
        """Plugin'in ana PHP dosyasındaki 'Version: x.y.z' üst bilgisini oku."""
        path = Path(plugin_path)
        candidates = []
        if path.is_dir():
            candidates.append(path / f"{path.name}.php")
            candidates.append(path / "index.php")
            candidates.extend(sorted(path.glob("*.php")))
        elif path.is_file():
            candidates = [path]

        for php in candidates:
            if not php.exists() or not php.is_file():
                continue
            try:
                text = php.read_text(encoding="utf-8", errors="replace")[:5000]
            except Exception:
                continue
            m = re.search(r"Version:\s*([0-9][0-9A-Za-z.\-]*)", text)
            if m:
                return m.group(1).strip()
        return None

    # ----------------------------------------------------------
    # 2) NVD'de CVE ara
    # ----------------------------------------------------------
    def query_keywords(self, keyword: str, per_page: int = 60) -> List[Dict]:
        """NVD API 2.0 keywordSearch ile CVE kayıtlarını getir."""
        params = {"keywordSearch": keyword, "resultsPerPage": per_page}
        try:
            r = requests.get(self.api, params=params, headers=self.headers, timeout=40)
            if r.status_code == 200:
                return r.json().get("vulnerabilities", [])
            if r.status_code in (403, 429):
                _print("ℹ️ NVD rate limit. Birkaç saniye bekleyip tekrar deneyin "
                         "veya .env'ye NVD_API_KEY ekleyin (ücretsiz).", "y")
            else:
                _print(f"❌ NVD API hata: HTTP {r.status_code}")
        except requests.exceptions.Timeout:
            _print("❌ NVD API timeout", "r")
        except Exception as e:
            _print(f"❌ NVD API hatası: {e}", "r")
        return []

    def match_plugin_slug(self, slug: str) -> List[Dict]:
        """Bir plugin slug'ı için olası tüm ilgili CVE'leri topla."""
        all_cves, seen = [], set()
        for keyword in (slug, f"{slug} plugin", f"wp-{slug}"):
            items = self.query_keywords(keyword, per_page=60)
            for it in items:
                cve = it.get("cve", {})
                cid = cve.get("id")
                if cid and cid not in seen:
                    seen.add(cid)
                    all_cves.append(cve)
        return all_cves

    def fetch_by_id(self, cve_id: str) -> Optional[Dict]:
        """Tek bir CVE ID ile ayrıntılı kayıt getir (NVD 2.0)."""
        items = self.query_keywords(cve_id, per_page=1)
        return items[0].get("cve") if items else None

    # ----------------------------------------------------------
    # 3) Versiyon aralığı eşleştirme
    # ----------------------------------------------------------
    @staticmethod
    def _parse_version(v: str) -> tuple:
        m = re.match(r"([0-9]+)((?:\.([0-9]+))?)", v.strip())
        if not m:
            return ()
        base = int(m.group(1))
        second = int(m.group(3)) if m.group(2) else 0
        return (base, second)

    @staticmethod
    def _tuple_le(a: tuple, b: tuple) -> bool:
        return a <= b

    def version_in_ranges(self, version: Optional[str], ranges: List[Dict]) -> Optional[str]:
        """Sürümü etkilenen aralıklarla karşılaştır.
        Dönen: 'etkilenen' | 'etkilenmedi' | None (bilinemez)."""
        if not version:
            return None
        vp = self._parse_version(version)
        if not vp:
            return None

        # Aralık verisi hiç yoksa -> ne oldugu bilinmez (sadece bilgi ver)
        for rng in ranges:
            start = rng.get("startIncluding")
            end = rng.get("endIncluding")
            end_excl = rng.get("endExcluding")

            match = True
            if start:
                sp = self._parse_version(start)
                if sp and not self._tuple_le(sp, vp):
                    match = False
            if end:
                ep = self._parse_version(end)
                if ep and not self._tuple_le(vp, ep):
                    match = False
            if end_excl:
                ep = self._parse_version(end_excl)
                if ep and not self._tuple_le(vp, ep):
                    # eşitliği dışarıda bırak: vp < end
                    if vp == ep:
                        match = False
            if match:
                return "yes"
        return "no" if ranges else None

    def _collect_ranges(self, cve: Dict) -> List[Dict]:
        """CVE configurations(node) yapısından etkilenen sürüm aralıklarını topla."""
        ranges = []
        for cfg in cve.get("configurations", []):
            for node in cfg.get("nodes", []):
                for m in node.get("cpeMatch", []):
                    if not m.get("vulnerable"):
                        continue
                    crit = m.get("criteria", "")
                    # yalnızca WordPress ÇEKİRDEĞİ'nin (özgün WP değil, eklenti) CPE'lerini atla:
                    # cpe:2.3:a:wordpress:wordpress:* (ürün adı "wordpress" olan boş sürüm)
                    if re.search(r":a:wordpress:wordpress:", crit) and "*" in crit.split(":")[-2:]:
                        continue
                    ranges.append({
                        "criteria": m.get("criteria", ""),
                        "startIncluding": m.get("versionStartIncluding", ""),
                        "endIncluding": m.get("versionEndIncluding", ""),
                        "endExcluding": m.get("versionEndExcluding", ""),
                    })
        return ranges

    # ----------------------------------------------------------
    # 4) Sunum + PoC şablonu
    # ----------------------------------------------------------
    def _describe(self, cve: Dict) -> str:
        for d in cve.get("descriptions", []):
            if d.get("lang") == "en":
                return d.get("value", "")
        return ""

    def _cvss(self, cve: Dict):
        for k in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if k in cve.get("metrics", {}):
                data = cve["metrics"][k][0].get("cvssData", {})
                return data.get("baseScore"), data.get("baseSeverity") or data.get("severity")
        return None, None

    def _refs(self, cve: Dict) -> List[str]:
        return [r.get("url") for r in cve.get("references", []) if r.get("url")]

    def print_cve(self, cve: Dict, version: Optional[str]) -> Dict:
        cid = cve.get("id", "?")
        score, sev = self._cvss(cve)
        ranges = self._collect_ranges(cve)
        still = version_in_ranges = self.version_in_ranges(version, ranges)

        result = {
            "id": cid,
            "cvss": score,
            "severity": sev,
            "published": (cve.get("published") or "")[:10],
            "description": self._describe(cve),
            "references": self._refs(cve),
            "affected_ranges": ranges,
            "match": still,
        }

        sev_c = {"CRITICAL": "r", "HIGH": "r", "MEDIUM": "y", "LOW": "g"}.get((sev or "").upper(), "reset")
        print("")
        _print(f"• {cid}", "bold")
        print(f"  Yayın: {result['published']}  CVSS: {score or '?'} ({sev or '?'})")
        print(f"  Durum: {still or 'bilinmiyor'}")
        desc = result["description"][:220].replace("\n", " ")
        print(f"  {desc}")
        return result


def generate_poc_template(cve_id, slug, version, description, refs) -> str:
    """Manuel PoC yazmak için Markdown iskeleti."""
    lines = [
        f"# PoC — {cve_id} · {slug}",
        "",
        "> Bu doküman yalnızca eğitim / yetkili test amaçlıdır.",
        "",
        "## Hedef",
        f"- Eklenti: `{slug}`",
        f"- Etkilenen sürüm: `{version or 'belirlenemedi'}`",
        "",
        "## Zafiyet",
        description or "_(NVD açıklaması buraya)_",
        "",
        "## Adımlar (manuel doğrulama)",
        "```bash",
        "# 1. Kurulum: hedef WP/PHP (sürüm = etkilenen sürüm)",
        f"# 2. Zafiyetli dosya/parametre: __DOSYAYI_BELİRT__",
        f"# 3. Erişim: /wp-content/plugins/{slug}/...",
        "```",
        "",
        "## PoC",
        "```python",
        "import requests",
        "",
        'HEDEF = "http://localhost"',
        "",
        "r = requests.get(HEDEF + '/...')",
        "print(r.status_code, r.text[:200])",
        "```",
        "",
        "## Referanslar",
        "".join(f"- {x}\n" for x in refs) or "- _(yok)_",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="WordPress CVE eşleştirici (NVD)")
    ap.add_argument("--slug", help="WordPress.org plugin slug (örn: advanced-custom-fields)")
    ap.add_argument("--version", help="Eklenti sürümü (ops., default plugin'den okunur)")
    ap.add_argument("--plugin-path", help="İndirilmiş plugin dizini / ana PHP yolu")
    ap.add_argument("--cve", help="Tek CVE ID'si (örn: CVE-2023-2234)")
    args = ap.parse_args()

    matcher = CVEMatcher()

    if args.cve:
        cve = matcher.fetch_by_id(args.cve)
        if not cve:
            _print("❌ CVE bulunamadı (hata/yok).", "r")
            return
        matcher.print_cve(cve, None)
        return

    if not args.slug and not args.plugin_path:
        ap.print_help()
        print("\n❌ En az --slug veya --plugin-path verilmelidir.")
        return

    version = args.version
    if args.plugin_path and version is None:
        version = matcher.extract_version_from_plugin(args.plugin_path)

    slug = args.slug or Path(args.plugin_path).name
    plugin_out_dir = Path(config.RESULTS_DIR) / "poc"

    print(f"🔎 '{slug}' için NVD taraması..." + (f" (sürüm: {version})" if version else " (sürüm belirsiz)"))
    cves = matcher.match_plugin_slug(slug)
    if not cves:
        _print("ℹ️ Eşleşen bilinen CVE bulunamadı. Yine de solukla bitebilir.", "y")
        return

    print(f"📦 {len(cves)} CVE kaydı bulundu; sürümle eşleştiriliyor...")
    matched_ids = []
    for cve in cves:
        info = matcher.print_cve(cve, version)
        if info and info.get("match") == "yes":
            matched_ids.append(info)

    # PoC şablonları yaz
    if matched_ids:
        plugin_out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📝 {len(matched_ids)} eşleşen CVE için PoC şablonu üretiliyor...")
        for info in matched_ids:
            fname = re.sub(r"[^A-Za-z0-9_\-]", "_", info["id"])
            fpath = plugin_out_dir / f"{fname}.md"
            fpath.write_text(generate_poc_template(info["id"], slug, version, info["description"], info["references"]), encoding="utf-8")
            print(f"   ✓ {fpath}")


if __name__ == "__main__":
    main()