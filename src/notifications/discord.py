from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Dict, Optional

from src.config import Settings
from src.notifications.base import Notifier
from src.storage.database import Database
from src.utils import utc_now_iso


class DiscordNotifier(Notifier):
    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db

    def send_daily(self, payload: Dict) -> Dict:
        run_date = payload["date"]
        page_url = payload["page_url"]
        key = f"daily:{run_date}"
        existing = self.db.query("SELECT * FROM discord_notifications WHERE notification_key = ?", (key,))
        if existing and not payload.get("force"):
            return {"status": "skipped", "reason": "already_notified", "message_id": existing[0]["message_id"]}
        message = {
            "content": f"📚 {run_date}のまとめを公開しました\n{page_url}",
            "embeds": [
                {
                    "title": f"{run_date} AIデイリー収集",
                    "url": page_url,
                    "description": f"合計 {payload.get('total', 0)}件 / 特におすすめ {payload.get('high', 0)}件 / 新規発見 {payload.get('discovery', 0)}件",
                    "fields": [
                        {"name": "上位カテゴリ", "value": payload.get("top_category", "未集計"), "inline": True},
                        {"name": "最高スコア", "value": str(payload.get("top_score", "-")), "inline": True},
                    ],
                    "footer": {"text": "AI Daily Collection"},
                }
            ],
        }
        result = self._post(self.settings.discord_daily_webhook_url, message)
        self.db.execute(
            "INSERT OR REPLACE INTO discord_notifications(notification_key, run_date, message_id, status, posted_at, page_url) VALUES (?, ?, ?, ?, ?, ?)",
            (key, run_date, result.get("id", ""), result.get("status", "sent"), utc_now_iso(), page_url),
        )
        return result

    def send_favorite(self, payload: Dict) -> Dict:
        message = {
            "content": "⭐ Favoriteに追加されました",
            "embeds": [
                {
                    "title": payload["title"],
                    "url": payload["url"],
                    "description": payload.get("excerpt", "")[:240],
                    "fields": [
                        {"name": "投稿者", "value": payload.get("author") or "unknown", "inline": True},
                        {"name": "カテゴリ", "value": payload.get("category") or "unknown", "inline": True},
                        {"name": "推薦スコア", "value": str(payload.get("score", "-")), "inline": True},
                        {"name": "Favorite日時", "value": payload.get("favorited_at", ""), "inline": False},
                        {"name": "日次まとめ", "value": payload.get("daily_url", ""), "inline": False},
                    ],
                    "footer": {"text": "AI Daily Collection"},
                }
            ],
        }
        return self._post(self.settings.discord_clipboard_webhook_url, message)

    @staticmethod
    def _post(webhook_url: str, body: Dict) -> Dict:
        if not webhook_url:
            return {"status": "skipped", "reason": "webhook_not_configured"}
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    text = response.read().decode("utf-8")
                    return json.loads(text) if text else {"status": "sent"}
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return {"status": "failed", "error": f"HTTP {exc.code}"}
            except urllib.error.URLError as exc:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                return {"status": "failed", "error": str(exc)}
        return {"status": "failed"}

