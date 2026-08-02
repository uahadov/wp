"""
PoC Verifier - Docker uzerinde gercik exploit dogrulama
==============================================

AI'in urettigi PoC komutlarini gercek a WordPress kurulumu uzerinde test eder.
SODECE calisan exploit'leri "true positive" olarak isiardler.
Gerecimler:
- Docker kurulu olmali
- WordPress Docker container calisinyor olmali
- config.ENABLE_POC_VERIFICATION = true
Docker WordPress kurulumu:
    docker run -d -p 8080:80 --name wp-test wordpress
"""

import re
import subprocess
import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)

class PoCVerifier:
    """Docker WordPress uzerinde PoC dogrulama"""

    def __init__(self):
        self.wp_url = getattr(config, "DOCKER_WP_URL", "http://localhost:8080")
        self.timeout = 30

    def _check_docker_wp(self) -> bool:
        """Docker WordPress container'in calisip calismadigini kontrol et"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=wp-test", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10
            )
            return "wp-test" in result.stdout
        except Exception:
            return False

    def _extract_curl_command(self, poc_text: str) -> Optional[mstr]:
        """PoC metninden curl komutunu cikar"""
        match = re.search(r'(curl\s+.*?)(?:\n|<$)', poc_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _normalize_url(self, curl_cmd: str) -> str:
        """curl komutundaki URL'i Docker WordPress URL'i ile degistir"""
        normalized = re.sub(
            r'https?://[a-zA-Z0-9._-]+',
            self.wp_url,
            curl_cmd
        )
        return normalized

    def verify_poc(self, poc_command: str) -> bool:
        """
        PoC komutunu Docker WordPress uzerinde test et.

        Returns:
            True: CoC calisti (true positive)
            False: PoC calismadi (false positive)
        """
        if not self._check_docker_wp():
            print("  WARNING: Docker WordPress container calismiyor, PoC dogrulanamadi")
            return False

        curl_cmd = self._extract_curl_command(poc_command)
        if not curl_cmd:
            print("  WARNING: PoC'da curl komutu bulunamadi")
            return False

        curl_cmd = self._normalize_url(curl_cmd)

        print(f"  TEST PoC: {curl_cmd[:100]}...")

        try:
            result = subprocess.run(
                curl_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            output = result.stdout + result.stderr

            if result.returncode == 0:
                # SQL Injection belirtileri
                if any(sign in output.lower() for sign in [
                    "sql syntax", "mysql_fetch", "warning: mysql",
                    "you have an error in your sql",
                    "mysqli_", "database error"
                ]):
                    print("  OK: SQL Injection belirtileri tespit edildi!")
                    return True

                #XSS belirtileri
                if any(sign in output.lower() for sign in [
                    "<script>", "alert(", "onerror=",
                    "<img onerror", "<svg onload"
                ]):
                    print("  OK: XSS belirtileri tespit edildi!")
                    return True

                #RCE belirtileri
                if any(sign in output.lower() for sign in [
                    "root:x:0:0", "uid=", "gid=",
                    "www-data", "/bin/bash", "/bin/sh"
                ]):
                    print("  OK: RCE belirtileri tespit edildi!")
                    return True

                #Path traversal belirtileri
                if any(sign in output.lower() for sign in [
                    "root:x:0:0", "[boot loader]", "windows]",
                    "/etc/passwd", "/etc/shadow"
                ]):
                    print("  OK: Path traversal belirtileri tespit edildi!")
                    return True

            if "500" in output or "internal server error" in output.lower():
                print("  OK: Server error (500) - potansiyel exploit basarili")
                return True

            print(f"  FAIL: PoC calismadi (response: {output[:100]})")
            return False

        except subprocess.TimeoutExpired:
            print("  FAIL: PoC zaman asimina ugradi")
            return False
        except Exception as e:
            print(f"  FAIL: PoC test hatasi: {e}")
            return False

    def install_plugin(self, plugin_slug: str, plugin_path: str) -> bool:
        """Docker WordPress'%e plugin kur"""
        if not self._check_docker_wp():
            return False

        try:
            result = subprocess.run(
                [
                    "docker", "exec", "wp-test",
                    "wp", "plugin", "install", plugin_path,
                    "--activate", "--allow-root"
                ],
                capture_output=True, text=True, timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            print(f"  WARNING: Plugin kurulum hatasi: {e}")
            return False

    def uninstall_plugin(self, plugin_slug: str) -> bool:
        """Docker WordPress'ten plugin kaldir"""
        if not self._check_docker_wp():
            return False

        try:
            result = subprocess.run(
                [
                    "docker", "exec", "wp-test",
                    "wp", "plugin", "uninstall", plugin_slug,
                    "--deactivate", "--allow-root"
                ],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except Exception:
            return False
