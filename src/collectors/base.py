from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from src.types import Candidate
from src.utils import extract_domain


class Collector(ABC):
    source = "base"

    @abstractmethod
    def collect(self, profile: Dict, since_hours: int = 48) -> List[Candidate]:
        raise NotImplementedError


def sample_candidates(source: str) -> List[Candidate]:
    now = datetime.now(timezone.utc)
    data = [
        Candidate(
            "Motion typography identity for a music label",
            "https://x.com/studio_type/status/1234567890",
            source,
            author="studio_type",
            text="experimental typography logo animation motion identity",
            tags=["typography", "motion"],
            published_at=now - timedelta(hours=6),
            media_type="video",
            domain=extract_domain("https://x.com/studio_type/status/1234567890"),
        ),
        Candidate(
            "3D printed hinge for modular shelf furniture",
            "https://maker.example/blog/modular-shelf-hinge?utm_source=x",
            source,
            author="maker-lab",
            text="functional 3d print compact furniture shelf gadget useful item",
            tags=["3d-print", "furniture"],
            published_at=now - timedelta(hours=18),
            media_type="article",
            domain="maker.example",
            discovery=True,
        ),
        Candidate(
            "VRChat world lighting breakdown",
            "https://x.com/worldbuilder/status/2222222222",
            source,
            author="worldbuilder",
            text="VRChat world virtual architecture spatial design lighting tips",
            tags=["vrchat", "world"],
            published_at=now - timedelta(hours=10),
            media_type="article",
            domain="x.com",
        ),
        Candidate(
            "Generic affiliate gadget sale",
            "https://shop.example/sale",
            source,
            author="dealbot",
            text="buy now best sale affiliate limited coupon",
            tags=["sale"],
            published_at=now - timedelta(hours=3),
            media_type="article",
            domain="shop.example",
        ),
        Candidate(
            "Unverified miracle posture health hack",
            "https://health.example/miracle-posture",
            source,
            author="healthtips",
            text="miracle cure posture health hack no evidence",
            tags=["health"],
            published_at=now - timedelta(hours=4),
            media_type="article",
            domain="health.example",
        ),
    ]
    return data

