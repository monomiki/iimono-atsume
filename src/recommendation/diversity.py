from __future__ import annotations

from collections import Counter
from typing import Iterable, List

from src.types import Recommendation


def apply_diversity(recommendations: Iterable[Recommendation], max_per_author: int = 3, max_per_category: int = 12) -> List[Recommendation]:
    authors = Counter()
    categories = Counter()
    result: List[Recommendation] = []
    for rec in sorted(recommendations, key=lambda item: item.score, reverse=True):
        author = rec.candidate.author or rec.candidate.domain or "unknown"
        if authors[author] >= max_per_author:
            continue
        if categories[rec.category] >= max_per_category:
            continue
        authors[author] += 1
        categories[rec.category] += 1
        result.append(rec)
    return result

