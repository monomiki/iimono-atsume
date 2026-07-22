from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from src.collectors.base import Collector, sample_candidates
from src.types import Candidate
from src.utils import extract_domain


class WebCollector(Collector):
    source = "web"

    def __init__(self, sources_path: Path):
        self.sources_path = sources_path

    def collect(self, profile: Dict, since_hours: int = 48) -> List[Candidate]:
        feeds = self._feeds()
        candidates: List[Candidate] = []
        for feed_url in feeds:
            try:
                candidates.extend(self._collect_feed(feed_url))
            except Exception:
                continue
        if not candidates:
            candidates = sample_candidates(self.source)[:3]
        return candidates

    def _feeds(self) -> List[str]:
        if not self.sources_path.exists():
            return []
        text = self.sources_path.read_text(encoding="utf-8")
        feeds = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- http"):
                feeds.append(stripped[2:].strip())
        return feeds

    def _collect_feed(self, feed_url: str) -> List[Candidate]:
        with urllib.request.urlopen(feed_url, timeout=10) as response:
            root = ET.fromstring(response.read())
        candidates = []
        for item in root.findall(".//item")[:20]:
            title = item.findtext("title") or ""
            link = item.findtext("link") or feed_url
            description = item.findtext("description") or ""
            candidates.append(
                Candidate(
                    title=title,
                    url=link,
                    source=self.source,
                    text=description,
                    published_at=datetime.now(timezone.utc),
                    domain=extract_domain(link),
                )
            )
        return candidates

