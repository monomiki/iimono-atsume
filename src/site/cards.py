from __future__ import annotations

import html
import json
from hashlib import sha256
from typing import Dict, List

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
        images=[],
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
    details = "".join(f"<li>{html.escape(reason)}</li>" for reason in item.reasons)
    novelty = "".join(f"<li>{html.escape(note)}</li>" for note in item.novelty)
    excerpt = html.escape(item.excerpt or item.title)
    title = html.escape(item.title)
    author = html.escape(item.author or "unknown")
    handle = f"@{author}" if item.author else "@unknown"
    category = html.escape(item.category)
    source = html.escape(item.source)
    url = html.escape(item.url, quote=True)
    published = html.escape(item.published_at[:16].replace("T", " ") if item.published_at else item.daily_page)
    item_json = html.escape(json.dumps({"item_id": item.item_id, "daily_page": item.daily_page}, ensure_ascii=False), quote=True)
    media = render_media(item)
    avatar_seed = html.escape((item.author or item.source or "?")[:2].upper())
    is_preview_favorite = item.item_id == "preview_fav"
    details_open = " open" if item.item_id == "preview_open" else ""
    favorite_class = "favorite-button is-favorited" if is_preview_favorite else "favorite-button"
    favorite_label = "★ Favorited" if is_preview_favorite else "☆ Favorite"
    favorite_state = "true" if is_preview_favorite else "false"
    favorite_icon, favorite_text = favorite_label[0], favorite_label[1:]
    return f"""
<article class="post-card link-card" data-item-id="{html.escape(item.item_id, quote=True)}" data-category="{category}" data-source="{source}" data-score="{item.score}" data-date="{html.escape(item.published_at or item.daily_page, quote=True)}" data-destination="{html.escape(item.destination, quote=True)}" data-discovery="{str(item.discovery).lower()}" data-favorite-state="{favorite_state}">
  <div class="post-card__content">
    <header class="post-card__author">
      <div class="post-card__avatar" aria-hidden="true">{avatar_seed}</div>
      <div class="post-card__identity">
        <strong class="post-card__display-name">{author}</strong>
        <span class="post-card__handle">{html.escape(handle)} · {source}</span>
      </div>
      <button class="{favorite_class}" type="button" data-favorite='{item_json}' aria-label="Favorite {title}">
        <span aria-hidden="true">{favorite_icon}</span><span class="favorite-button__label">{html.escape(favorite_text)}</span>
      </button>
    </header>
    <h3 class="post-card__title">{title}</h3>
    <p class="post-card__body" data-collapsible>{excerpt}</p>
    {media}
    <div class="post-card__ai-summary">
      <span>AI {item.score}</span>
      <span title="{category}">{category}</span>
    </div>
    <details class="post-card__details"{details_open}>
      <summary>推薦情報</summary>
      <div class="post-card__details-body">
        <p>{reason}</p>
        <ul>{details}{novelty}</ul>
      </div>
    </details>
    <footer class="post-card__footer">
      <span>{source}</span>
      <span>{published}</span>
      <a href="{url}" rel="noopener noreferrer" target="_blank">元投稿を見る</a>
    </footer>
  </div>
</article>
""".strip()


def render_media(item: SiteItem) -> str:
    images = item.images or ([{"url": item.image_url, "alt": item.title}] if item.image_url else [])
    images = [image for image in images if image.get("url")]
    if item.media_type == "video" and not images:
        return """
<div class="post-card__media post-card__media--video" aria-label="動画">
  <div class="post-card__video-placeholder">VIDEO</div>
</div>
""".strip()
    if not images:
        return ""
    visible = images[:4]
    more = max(0, len(images) - len(visible))
    image_html: List[str] = []
    for index, image in enumerate(visible):
        src = html.escape(image["url"], quote=True)
        alt = html.escape(image.get("alt", ""), quote=True)
        width = html.escape(str(image.get("width", "")), quote=True)
        height = html.escape(str(image.get("height", "")), quote=True)
        attrs = f' width="{width}" height="{height}"' if width and height else ""
        loading = "eager" if index == 0 else "lazy"
        overlay = f'<span class="post-card__more">+{more}</span>' if more and index == len(visible) - 1 else ""
        image_html.append(f'<figure><img src="{src}" alt="{alt}"{attrs} loading="{loading}" decoding="async">{overlay}</figure>')
    return f'<div class="post-card__media post-card__media--count-{len(images)}">{"".join(image_html)}</div>'
