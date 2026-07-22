from __future__ import annotations

from collections import Counter
from math import sqrt
from typing import Dict

from src.utils import tokenize


class KeywordEmbeddingModel:
    """Small local embedding substitute. Replace with OpenAI or another provider later."""

    def embed(self, text: str) -> Dict[str, float]:
        counts = Counter(tokenize(text))
        norm = sqrt(sum(v * v for v in counts.values())) or 1.0
        return {key: value / norm for key, value in counts.items()}

    @staticmethod
    def similarity(a: Dict[str, float], b: Dict[str, float]) -> float:
        return sum(a.get(key, 0.0) * b.get(key, 0.0) for key in set(a) | set(b))

