from __future__ import annotations

from typing import Iterable, List, Set, Tuple

from src.types import Bookmark, Candidate
from src.utils import normalize_url, post_identity, similar_text


class Deduplicator:
    def __init__(self, existing_bookmarks: Iterable[Bookmark]):
        self.existing_urls: Set[str] = {normalize_url(b.url) for b in existing_bookmarks}
        self.existing_ids: Set[str] = {post_identity(b.url) for b in existing_bookmarks}
        self.existing_titles: List[str] = [b.title for b in existing_bookmarks if b.title]

    def filter(self, candidates: Iterable[Candidate]) -> Tuple[List[Candidate], List[Tuple[Candidate, str]]]:
        kept: List[Candidate] = []
        removed: List[Tuple[Candidate, str]] = []
        seen: Set[str] = set()
        for candidate in candidates:
            normalized = normalize_url(candidate.url)
            identity = post_identity(candidate.url)
            if normalized in self.existing_urls or identity in self.existing_ids:
                removed.append((candidate, "既存ライブラリに保存済み"))
                continue
            if identity in seen:
                removed.append((candidate, "同一投稿のミラーURL"))
                continue
            if any(similar_text(candidate.title, title) > 0.92 for title in self.existing_titles):
                removed.append((candidate, "タイトルが既存コンテンツと類似"))
                continue
            seen.add(identity)
            kept.append(candidate)
        return kept, removed

