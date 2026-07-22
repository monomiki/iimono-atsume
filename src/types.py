from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Collection:
    id: int
    title: str
    count: int = 0
    parent_id: Optional[int] = None
    created: str = ""
    last_update: str = ""


@dataclass
class Bookmark:
    id: int
    title: str
    url: str
    domain: str = ""
    excerpt: str = ""
    note: str = ""
    tags: List[str] = field(default_factory=list)
    collection_id: Optional[int] = None
    collection_title: str = ""
    created: str = ""
    last_update: str = ""
    media_type: str = "link"
    cover: str = ""


@dataclass
class Candidate:
    title: str
    url: str
    source: str
    author: str = ""
    text: str = ""
    tags: List[str] = field(default_factory=list)
    published_at: Optional[datetime] = None
    media_type: str = "link"
    image_url: str = ""
    domain: str = ""
    discovery: bool = False
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Recommendation:
    candidate: Candidate
    score: int
    category: str
    reasons: List[str]
    novelty: List[str]
    score_breakdown: Dict[str, float]
    destination: str


@dataclass
class SiteItem:
    item_id: str
    title: str
    url: str
    normalized_url: str
    source: str
    author: str
    excerpt: str
    published_at: str
    media_type: str
    image_url: str
    score: int
    category: str
    reasons: List[str]
    novelty: List[str]
    daily_page: str
    destination: str
    discovery: bool = False
    images: List[Dict[str, str]] = field(default_factory=list)
