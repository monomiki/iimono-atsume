from __future__ import annotations

from typing import Dict, List

from src.collectors.base import Collector, sample_candidates
from src.types import Candidate


class XCollector(Collector):
    source = "x"

    def __init__(self, bearer_token: str = ""):
        self.bearer_token = bearer_token

    def collect(self, profile: Dict, since_hours: int = 48) -> List[Candidate]:
        if not self.bearer_token:
            return [c for c in sample_candidates(self.source) if c.source == self.source]
        # Official X API integration point. The rest of the pipeline is isolated
        # so this adapter can be expanded without changing scoring or storage.
        return sample_candidates(self.source)

