from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Iterable, List, Set
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "igshid", "ref"}
X_HOSTS = {"twitter.com", "www.twitter.com", "x.com", "www.x.com", "fxtwitter.com", "vxtwitter.com", "fixupx.com"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = re.sub(r"/+$", "", parsed.path)
    query_items = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in TRACKING_PARAMS]
    if netloc in X_HOSTS:
        netloc = "x.com"
        match = re.search(r"/([^/]+)/status(?:es)?/(\d+)", path)
        if match:
            path = f"/{match.group(1)}/status/{match.group(2)}"
            query_items = []
    if netloc in {"instagram.com", "www.instagram.com"}:
        netloc = "www.instagram.com"
        query_items = []
    return urlunparse((scheme, netloc, path, "", urlencode(query_items), ""))


def post_identity(url: str) -> str:
    normalized = normalize_url(url)
    parsed = urlparse(normalized)
    if parsed.netloc == "x.com":
        match = re.search(r"/status/(\d+)", parsed.path)
        if match:
            return f"x:{match.group(1)}"
    if parsed.netloc == "www.instagram.com":
        match = re.search(r"/(p|reel|tv)/([^/]+)", parsed.path)
        if match:
            return f"instagram:{match.group(1)}:{match.group(2)}"
    return normalized


def text_fingerprint(parts: Iterable[str]) -> str:
    text = " ".join(part or "" for part in parts).lower()
    text = re.sub(r"\s+", " ", text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def tokenize(text: str) -> Set[str]:
    return set(re.findall(r"[a-zA-Z0-9_#]+|[\u3040-\u30ff\u3400-\u9fff]+", text.lower()))


def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def similar_text(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def extract_domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def score_tag(score: int) -> str:
    rounded = max(0, min(100, int(round(score / 10.0) * 10)))
    return f"score-{rounded}"

