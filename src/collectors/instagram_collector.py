from __future__ import annotations

from typing import Dict, List

from src.collectors.base import Collector, sample_candidates
from src.types import Candidate


class InstagramCollector(Collector):
    source = "instagram"

    def __init__(self, access_token: str = ""):
        self.access_token = access_token

    def collect(self, profile: Dict, since_hours: int = 48) -> List[Candidate]:
        if not self.access_token:
            candidate = sample_candidates(self.source)[1]
            candidate.url = "https://www.instagram.com/p/ABC123/?igshid=demo"
            candidate.source = self.source
            candidate.author = "spatial_objects"
            return [candidate]
        return sample_candidates(self.source)[:2]

