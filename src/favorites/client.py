from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from src.config import Settings
from src.favorites.feedback import apply_favorite_feedback
from src.storage.database import Database
from src.utils import post_identity, utc_now_iso


class FavoriteService:
    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db

    def favorite(self, item_id: str, daily_page: str, authenticated: bool = False) -> Dict:
        if not authenticated:
            return {"status": "forbidden"}
        item = self._load_item(item_id)
        if not item or item.get("daily_page") != daily_page:
            return {"status": "not_found"}
        dedupe_key = post_identity(item["normalized_url"])
        existing = self.db.query("SELECT * FROM favorites WHERE dedupe_key = ?", (dedupe_key,))
        if existing:
            return {"status": "already_favorited", "item_id": item_id, "discord_status": existing[0]["discord_status"]}
        favorited_at = utc_now_iso()
        discord_status = "tagged"
        self.db.execute(
            "INSERT INTO favorites(item_id, normalized_url, title, favorited_at, category, score, daily_page, discord_status, discord_message_id, dedupe_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (item_id, item["normalized_url"], item["title"], favorited_at, item["category"], item["score"], daily_page, discord_status, "", dedupe_key),
        )
        apply_favorite_feedback(self.db, item["normalized_url"], item["category"])
        return {"status": "favorited", "item_id": item_id, "discord_status": discord_status}

    def resend_pending(self) -> Dict:
        rows = self.db.query("SELECT * FROM favorites WHERE discord_status = 'pending'")
        return {"pending": len(rows), "sent": 0, "status": "skipped", "reason": "favorite_discord_forwarding_disabled"}

    def list_favorites(self) -> List[Dict]:
        return [dict(row) for row in self.db.query("SELECT * FROM favorites ORDER BY favorited_at DESC")]

    @staticmethod
    def _load_item(item_id: str) -> Dict:
        path = Path("data") / "items" / f"{item_id}.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
