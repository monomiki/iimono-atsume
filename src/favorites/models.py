from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Favorite:
    item_id: str
    normalized_url: str
    title: str
    favorited_at: str
    category: str
    score: int
    daily_page: str
    discord_status: str = "pending"
    discord_message_id: str = ""
    dedupe_key: str = ""

