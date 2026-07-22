from __future__ import annotations

import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict

from src.config import Settings


class SiteDeployer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def deploy(self, dry_run: bool = False) -> Dict:
        if dry_run or self.settings.dry_run:
            return {"status": "skipped", "reason": "dry_run"}
        if not self.settings.github_repository:
            return {"status": "skipped", "reason": "GITHUB_REPOSITORY is not configured"}
        if not self.settings.public_dir.exists():
            return {"status": "failed", "reason": "public directory does not exist"}
        subprocess.run(["git", "add", "-f", "public"], check=True)
        subprocess.run(["git", "add", "data", "reports"], check=True)
        status = subprocess.run(["git", "diff", "--cached", "--quiet"], check=False)
        if status.returncode == 0:
            return {"status": "skipped", "reason": "no site changes"}
        subprocess.run(["git", "commit", "-m", "Publish daily collection site"], check=True)
        subprocess.run(["git", "push"], check=True)
        return {"status": "deployed"}

    @staticmethod
    def verify(url: str) -> Dict:
        if not url:
            return {"status": "skipped", "reason": "url_not_configured"}
        try:
            request = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(request, timeout=20) as response:
                return {"status": "ok", "code": response.status}
        except urllib.error.URLError as exc:
            return {"status": "failed", "reason": str(exc)}
