from __future__ import annotations

import html
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict


META_RE = re.compile(r"<meta\s+[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(r"([a-zA-Z_:.-]+)\s*=\s*(['\"])(.*?)\2", re.IGNORECASE | re.DOTALL)
DIRECT_VIDEO_EXTENSIONS = (".mp4", ".webm", ".ogg", ".ogv", ".mov", ".m4v")


def enrich_link_metadata(url: str, timeout: int = 8) -> Dict[str, str]:
    if not url.startswith(("http://", "https://")):
        return {}
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI-Daily-Collection/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("content-type", "")
            body = response.read(512_000)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return {}
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        return {}
    page = body.decode("utf-8", "ignore")
    metadata = _extract_meta(page)
    base_url = response.geturl() or url
    image_url = _absolute_url(
        metadata.get("og:image:secure_url")
        or metadata.get("og:image")
        or metadata.get("twitter:image")
        or metadata.get("twitter:image:src")
        or _first_image_src(page),
        base_url,
    )
    video_url = _absolute_url(
        metadata.get("og:video:secure_url")
        or metadata.get("og:video:url")
        or metadata.get("og:video")
        or metadata.get("twitter:player:stream"),
        base_url,
    )
    result: Dict[str, str] = {}
    if image_url:
        result["image_url"] = image_url
    if video_url:
        result["video_url"] = video_url
    return result


def is_direct_video_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.path.lower().endswith(DIRECT_VIDEO_EXTENSIONS)


def _extract_meta(page: str) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    for tag in META_RE.findall(page):
        attrs = {key.lower(): html.unescape(value.strip()) for key, _, value in ATTR_RE.findall(tag)}
        key = (attrs.get("property") or attrs.get("name") or "").lower()
        content = attrs.get("content", "")
        if key and content:
            metadata[key] = content
    return metadata


def _first_image_src(page: str) -> str:
    match = re.search(r"<img\s+[^>]*src\s*=\s*(['\"])(.*?)\1", page, re.IGNORECASE | re.DOTALL)
    return html.unescape(match.group(2).strip()) if match else ""


def _absolute_url(url: str, base_url: str) -> str:
    if not url or url.startswith("data:"):
        return ""
    return urllib.parse.urljoin(base_url, html.unescape(url.strip()))
