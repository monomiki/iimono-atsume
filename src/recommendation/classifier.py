from __future__ import annotations

from typing import Dict

from src.preference.profiler import PreferenceProfiler
from src.types import Candidate


class CategoryClassifier:
    def classify(self, candidate: Candidate, profile: Dict) -> str:
        text = " ".join([candidate.title, candidate.text, " ".join(candidate.tags)]).lower()
        best_category = "fun_sensory"
        best_hits = -1
        for category in profile.get("categories", []):
            hits = sum(1 for feature in category.get("positive_features", []) if feature.lower() in text)
            if hits > best_hits:
                best_category = category["category"]
                best_hits = hits
        if best_hits <= 0:
            return PreferenceProfiler._category_for("", candidate.tags, text)
        return best_category

