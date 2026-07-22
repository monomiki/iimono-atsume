from __future__ import annotations

import html
import json
from hashlib import sha256
from typing import Dict

from src.types import Recommendation, SiteItem
from src.utils import normalize_url, post_identity


def item_id_for(rec: Recommendation) -> str:
    identity = post_identity(rec.candidate.url)
    digest = sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"{rec.candidate.source}_{digest}"


def site_item_from_recommendation(rec: Recommendation, run_date: str) -> SiteItem:
    candidate = rec.candidate
    return SiteItem(
        item_id=item_id_for(rec),
        title=candidate.title,
        url=normalize_url(candidate.url),
        normalized_url=normalize_url(candidate.url),
        source=candidate.source,
        author=candidate.author,
        excerpt=(candidate.text or "")[:220],
        published_at=candidate.published_at.isoformat() if candidate.published_at else "",
        media_type=candidate.media_type,
        image_url=candidate.image_url,
        score=rec.score,
        category=rec.category,
        reasons=rec.reasons,
        novelty=rec.novelty,
        daily_page=run_date,
        destination=rec.destination,
        discovery=candidate.discovery,
    )


def item_to_dict(item: SiteItem) -> Dict:
    return dict(item.__dict__)


def render_link_card(item: SiteItem) -> str:
    reason = html.escape(" / ".join(item.reasons[:2]))
    excerpt = html.escape(item.excerpt)
    title = html.escape(item.title)
    author = html.escape(item.author or "unknown")
    category = html.escape(item.category)
    source = html.escape(item.source)
    url = html.escape(item.url, quote=True)
    item_json = html.escape(json.dumps({"item_id": item.item_id, "daily_page": item.daily_page}, ensure_ascii=False), quote=True)
    thumbnail = (
        f'<img class="card-thumb" src="{html.escape(item.image_url, quote=True)}" alt="" loading="lazy">'
        if item.image_url
        else '<div class="card-thumb card-thumb-placeholder" aria-hidden="true"></div>'
    )
    return f"""
<article class="link-card" data-item-id="{html.escape(item.item_id, quote=True)}" data-category="{category}" data-source="{source}">
  {thumbnail}
  <div class="card-body">
    <div class="card-meta">@{author}・{source}</div>
    <h3>{title}</h3>
    <p class="excerpt">{excerpt}</p>
    <div class="card-badges">
      <span>推薦スコア {item.score}</span>
      <span>{category}</span>
    </div>
    <p class="reason">{reason}</p>
    <div class="card-actions">
      <a href="{url}" rel="noopener noreferrer" target="_blank">元投稿を見る</a>
      <button class="favorite-button" type="button" data-favorite='{item_json}'>☆ Favorite</button>
    </div>
  </div>
</article>
""".strip()

