from __future__ import annotations

from src.preference.feedback import FeedbackStore
from src.storage.database import Database


def apply_favorite_feedback(db: Database, url: str, category: str) -> None:
    FeedbackStore(db).record(url, "web_favorite", category, 10.0)

