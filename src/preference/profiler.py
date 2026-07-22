from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

from src.config import EXCLUDED_COLLECTION_NAMES, INTEREST_CATEGORIES
from src.types import Bookmark
from src.utils import extract_domain, tokenize


class PreferenceProfiler:
    def __init__(self, output_path: Path):
        self.output_path = output_path

    def build(self, bookmarks: Iterable[Bookmark]) -> Dict:
        grouped: Dict[str, List[Bookmark]] = defaultdict(list)
        for bookmark in bookmarks:
            if self._excluded(bookmark):
                continue
            category = self._category_for(bookmark.collection_title, bookmark.tags, bookmark.title + " " + bookmark.excerpt)
            grouped[category].append(bookmark)

        profiles = []
        total_counts = sum(len(v) for v in grouped.values()) or 1
        for category, items in sorted(grouped.items()):
            token_counts = Counter()
            domain_counts = Counter()
            media_counts = Counter()
            sample_ids = []
            for item in items:
                token_counts.update(tokenize(" ".join([item.title, item.excerpt, item.note, " ".join(item.tags)])))
                domain_counts.update([item.domain or extract_domain(item.url)])
                media_counts.update([item.media_type])
                sample_ids.append(item.id)
            normalized_interest = round((len(items) / total_counts) ** 0.5, 3)
            profiles.append(
                {
                    "category": category,
                    "normalized_interest": normalized_interest,
                    "positive_features": [word for word, _ in token_counts.most_common(15)],
                    "negative_features": self._negative_features(category),
                    "preferred_accounts": self._accounts(items),
                    "preferred_domains": [domain for domain, _ in domain_counts.most_common(10) if domain],
                    "media_types": dict(media_counts),
                    "sample_bookmark_ids": sample_ids[:20],
                }
            )
        profile = {"version": 1, "categories": profiles, "search_terms": self.search_terms(profiles)}
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        return profile

    def load(self) -> Dict:
        if not self.output_path.exists():
            return {"version": 1, "categories": [], "search_terms": []}
        return json.loads(self.output_path.read_text(encoding="utf-8"))

    @staticmethod
    def search_terms(profiles: List[Dict]) -> List[str]:
        base = [
            "graphic design", "editorial design", "experimental typography", "motion identity",
            "logo animation", "poster design", "character goods design", "product design",
            "packaging design", "spatial design", "virtual architecture", "VRChat world",
            "VRChat gimmick", "Blender tips", "3D printing", "functional print",
            "Japanese exhibition", "art exhibition Tokyo", "unusual furniture", "compact gadget",
        ]
        learned = []
        for profile in profiles:
            learned.extend(profile.get("positive_features", [])[:5])
        return sorted(set(base + learned))

    @staticmethod
    def _excluded(bookmark: Bookmark) -> bool:
        title = bookmark.collection_title or ""
        return title in EXCLUDED_COLLECTION_NAMES or "backup" in title.lower() or "旧" in title and "構成" in title

    @staticmethod
    def _category_for(collection_title: str, tags: List[str], text: str) -> str:
        for category, names in INTEREST_CATEGORIES.items():
            if collection_title in names:
                return category
        haystack = " ".join([collection_title, " ".join(tags), text]).lower()
        rules = {
            "design_graphic": ["logo", "typo", "poster", "graphic", "font", "ロゴ"],
            "vr_3d_tech": ["vrchat", "3d", "blender", "printer", "gadget", "ガジェット"],
            "life_product": ["家具", "fashion", "room", "health", "料理", "keyboard"],
            "culture_places": ["exhibition", "tokyo", "music", "漫画", "本", "event"],
            "illustration_video_space": ["illustration", "映像", "写真", "建築", "空間", "web"],
        }
        for category, words in rules.items():
            if any(word in haystack for word in words):
                return category
        return "fun_sensory"

    @staticmethod
    def _accounts(items: List[Bookmark]) -> List[str]:
        accounts = Counter()
        for item in items:
            parts = item.url.rstrip("/").split("/")
            if "x.com" in item.url or "twitter.com" in item.url or "instagram.com" in item.url:
                if len(parts) > 3:
                    accounts.update([parts[3]])
        return [account for account, count in accounts.most_common(10) if count > 1]

    @staticmethod
    def _negative_features(category: str) -> List[str]:
        common = ["広告目的だけの投稿", "内容の薄いまとめ投稿", "根拠のないTips"]
        if category == "life_product":
            return common + ["根拠のない健康情報", "終了済みセール"]
        return common + ["一般的すぎるテンプレート"]

