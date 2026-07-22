from __future__ import annotations

from typing import Dict

from src.storage.database import Database
from src.utils import normalize_url, utc_now_iso


class FeedbackStore:
    POSITIVE_TAGS = {"good", "もっと見たい"}
    NEGATIVE_TAGS = {"not-interested"}

    def __init__(self, db: Database):
        self.db = db

    def record(self, url: str, action: str, category: str = "", score_delta: float = 0.0) -> None:
        self.db.execute(
            "INSERT INTO feedback(url, normalized_url, action, category, score_delta, observed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (url, normalize_url(url), action, category, score_delta, utc_now_iso()),
        )

    def score_adjustments(self) -> Dict[str, float]:
        rows = self.db.query("SELECT normalized_url, SUM(score_delta) AS delta FROM feedback GROUP BY normalized_url")
        return {row["normalized_url"]: float(row["delta"] or 0.0) for row in rows}

