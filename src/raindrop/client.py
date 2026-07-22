from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Optional

from src.types import Bookmark, Collection, Recommendation
from src.utils import extract_domain, normalize_url, score_tag


class RaindropError(RuntimeError):
    pass


class RaindropClient:
    base_url = "https://api.raindrop.io/rest/v1"

    def __init__(self, access_token: str = "", timeout: int = 20, retries: int = 3):
        self.access_token = access_token
        self.timeout = timeout
        self.retries = retries

    @property
    def available(self) -> bool:
        return bool(self.access_token)

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        if not self.access_token:
            raise RaindropError("RAINDROP_ACCESS_TOKEN is not configured")
        data = None
        headers = {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < self.retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise RaindropError(f"Raindrop API error {exc.code}: {exc.read().decode('utf-8', 'ignore')}") from exc
            except urllib.error.URLError as exc:
                if attempt < self.retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise RaindropError(f"Raindrop API network error: {exc}") from exc
        raise RaindropError("Raindrop API request failed")

    def get_root_collections(self) -> List[Collection]:
        payload = self._request("GET", "/collections")
        return [self._parse_collection(item) for item in payload.get("items", [])]

    def get_child_collections(self) -> List[Collection]:
        payload = self._request("GET", "/collections/childrens")
        return [self._parse_collection(item) for item in payload.get("items", [])]

    def get_all_collections(self) -> List[Collection]:
        return self.get_root_collections() + self.get_child_collections()

    def ensure_daily_collections(self, names: Dict[str, str]) -> Dict[str, int]:
        collections = self.get_all_collections()
        root_id = self.resolve_collection_id(collections, names["root"], parent_id=None, create=True)
        refreshed = self.get_all_collections()
        result = {"root": root_id}
        for key in ("inbox", "high", "discovery", "negative"):
            result[key] = self.resolve_collection_id(refreshed, names[key], parent_id=root_id, create=True)
            refreshed = self.get_all_collections()
        return result

    def resolve_collection_id(self, collections: List[Collection], title: str, parent_id: Optional[int] = None, create: bool = False) -> int:
        matches = [c for c in collections if c.title == title and (parent_id is None or c.parent_id == parent_id)]
        if matches:
            best = sorted(matches, key=lambda c: (c.count, c.last_update, c.created), reverse=True)[0]
            return best.id
        if create:
            body = {"title": title, "view": "list"}
            if parent_id is not None:
                body["parent"] = {"$id": parent_id}
            payload = self._request("POST", "/collection", body)
            return int(payload["item"]["_id"])
        raise KeyError(f"Collection not found: {title}")

    def get_raindrops(self, collection_id: int, per_page: int = 50, max_items: int = 500) -> List[Bookmark]:
        items: List[Bookmark] = []
        page = 0
        while len(items) < max_items:
            query = urllib.parse.urlencode({"perpage": per_page, "page": page})
            payload = self._request("GET", f"/raindrops/{collection_id}?{query}")
            batch = [self._parse_bookmark(item) for item in payload.get("items", [])]
            if not batch:
                break
            items.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
        return items[:max_items]

    def create_raindrop(self, recommendation: Recommendation, collection_id: int) -> dict:
        candidate = recommendation.candidate
        note = self.recommendation_note(recommendation)
        tags = [
            "ai-collected",
            f"source-{candidate.source}",
            score_tag(recommendation.score),
            f"category-{recommendation.category}",
            "discovery" if candidate.discovery else "",
        ]
        tags.extend(candidate.tags)
        body = {
            "link": normalize_url(candidate.url),
            "title": candidate.title,
            "excerpt": candidate.text[:1000],
            "collection": {"$id": collection_id},
            "tags": sorted({tag for tag in tags if tag}),
            "note": note,
        }
        return self._request("POST", "/raindrop", body)

    @staticmethod
    def recommendation_note(recommendation: Recommendation) -> str:
        reasons = "\n".join(f"- {reason}" for reason in recommendation.reasons)
        novelty = "\n".join(f"- {item}" for item in recommendation.novelty) or "- 既存ライブラリとの差分は小さい"
        return (
            f"AI推薦スコア: {recommendation.score}/100\n"
            f"推定カテゴリ: {recommendation.category}\n"
            f"発見元: {recommendation.candidate.source}\n"
            f"推薦理由:\n{reasons}\n"
            f"新規性:\n{novelty}\n"
        )

    @staticmethod
    def _parse_collection(item: dict) -> Collection:
        parent = item.get("parent") or {}
        return Collection(
            id=int(item["_id"]),
            title=item.get("title", ""),
            count=int(item.get("count", 0) or 0),
            parent_id=parent.get("$id"),
            created=item.get("created", ""),
            last_update=item.get("lastUpdate", ""),
        )

    @staticmethod
    def _parse_bookmark(item: dict) -> Bookmark:
        collection = item.get("collection") or {}
        link = item.get("link", "")
        return Bookmark(
            id=int(item.get("_id", 0)),
            title=item.get("title", ""),
            url=link,
            domain=item.get("domain") or extract_domain(link),
            excerpt=item.get("excerpt", ""),
            note=item.get("note", ""),
            tags=item.get("tags") or [],
            collection_id=collection.get("$id"),
            created=item.get("created", ""),
            last_update=item.get("lastUpdate", ""),
            media_type=item.get("type", "link"),
            cover=item.get("cover", ""),
        )


def mock_bookmarks() -> List[Bookmark]:
    return [
        Bookmark(1, "Experimental typography poster archive", "https://example.com/type-poster", "example.com", "poster layout experimental typography", tags=["typo"], collection_title="😤typo", media_type="image"),
        Bookmark(2, "VRChat world with soft spatial lighting", "https://example.org/vrchat-world", "example.org", "virtual architecture world design", tags=["vrchat"], collection_title="🌍ワールド", media_type="article"),
        Bookmark(3, "Functional 3D printed desk hook", "https://maker.example/desk-hook", "maker.example", "3d printing furniture utility compact gadget", tags=["3d-print"], collection_title="🏭3dプリンター", media_type="article"),
        Bookmark(4, "Logo motion identity case study", "https://studio.example/logo-motion", "studio.example", "motion identity animated logo typography", tags=["logo"], collection_title="🟣logo_motion", media_type="video"),
        Bookmark(5, "Tokyo small exhibition guide", "https://culture.example/exhibit", "culture.example", "art exhibition tokyo spatial installation", tags=["event"], collection_title="📆展示・イベント", media_type="article"),
    ]

