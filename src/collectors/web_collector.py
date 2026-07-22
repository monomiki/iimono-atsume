from __future__ import annotations

import json
import re
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
            image_url, video_url, media_type = self._item_media(item, description)
            candidates.append(
                Candidate(
                    title=title,
                    url=link,
                    source=self.source,
                    text=description,
                    published_at=datetime.now(timezone.utc),
                    media_type=media_type,
                    image_url=image_url,
                    video_url=video_url,
                    domain=extract_domain(link),
                )
            )
        return candidates

    @staticmethod
    def _item_media(item: ET.Element, description: str) -> tuple[str, str, str]:
        image_url = ""
        video_url = ""
        media_type = "article"
        for child in item:
            tag = child.tag.lower()
            url = child.attrib.get("url", "")
            content_type = child.attrib.get("type", "")
            if not url:
                continue
            if tag.endswith("thumbnail") or content_type.startswith("image/"):
                image_url = image_url or url
            elif tag.endswith("content") or tag.endswith("enclosure"):
                if content_type.startswith("video/"):
                    video_url = video_url or url
                    media_type = "video"
                elif content_type.startswith("image/"):
                    image_url = image_url or url
                    media_type = "image"
        if not image_url:
            match = re.search(r"<img\s+[^>]*src\s*=\s*(['\"])(.*?)\1", description, re.IGNORECASE | re.DOTALL)
            image_url = match.group(2).strip() if match else ""
        return image_url, video_url, media_type
