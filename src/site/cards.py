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
        video_url=candidate.video_url,
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
    avatar = render_avatar(item)
    is_preview_favorite = item.item_id == "preview_fav"
    details_open = " open" if item.item_id == "preview_open" else ""
    favorite_class = "favorite-button is-favorited" if is_preview_favorite else "favorite-button"
    favorite_label = "★" if is_preview_favorite else "☆"
    favorite_state = "true" if is_preview_favorite else "false"
    source_key = source_key_for(item)
    return f"""
<article class="post-card link-card" data-item-id="{html.escape(item.item_id, quote=True)}" data-category="{category}" data-source="{source}" data-source-key="{html.escape(source_key, quote=True)}" data-score="{item.score}" data-date="{html.escape(item.published_at or item.daily_page, quote=True)}" data-destination="{html.escape(item.destination, quote=True)}" data-discovery="{str(item.discovery).lower()}" data-favorite-state="{favorite_state}">
  <div class="post-card__content">
    <header class="post-card__author">
      {avatar}
      <div class="post-card__identity">
        <a class="post-card__display-name" href="{url}" rel="noopener noreferrer" target="_blank">{author}</a>
        <span class="post-card__handle">{html.escape(handle)} · {source}</span>
      </div>
      <button class="{favorite_class}" type="button" data-favorite='{item_json}' aria-label="Favorite {title}">
        <span aria-hidden="true">{favorite_label}</span>
      </button>
    </header>
    <h3 class="post-card__title"><a href="{url}" rel="noopener noreferrer" target="_blank">{title}</a></h3>
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
    </footer>
  </div>
</article>
""".strip()


def render_avatar(item: SiteItem) -> str:
    image_url = avatar_image_url_for(item)
    label = html.escape((item.title or item.source or "リンク")[:40], quote=True)
    if image_url:
        src = html.escape(image_url, quote=True)
        return f'<div class="post-card__avatar post-card__avatar--image"><img src="{src}" alt="{label}" loading="lazy" decoding="async"></div>'
    avatar_seed = html.escape((item.author or item.source or "?")[:2].upper())
    return f'<div class="post-card__avatar post-card__avatar--fallback" aria-hidden="true">{avatar_seed}</div>'


def avatar_image_url_for(item: SiteItem) -> str:
    if item.image_url:
        return item.image_url
    for image in item.images:
        url = image.get("url", "")
        if url:
            return url
    return ""


def render_media(item: SiteItem) -> str:
    images = item.images or ([{"url": item.image_url, "alt": item.title}] if item.image_url else [])
    images = [image for image in images if image.get("url")]
    if item.media_type == "video":
        return render_video_media(item, images)
    if not images:
        return render_thumbnail_placeholder(item)
    return render_image_grid(images, link_url=item.url)


def render_video_media(item: SiteItem, images: List[Dict[str, str]]) -> str:
    poster = html.escape((images[0].get("url") if images else item.image_url) or "", quote=True)
    video_url = html.escape(item.video_url or "", quote=True)
    if item.video_url and is_direct_video_url(item.video_url):
        poster_attr = f' poster="{poster}"' if poster else ""
        return f"""
<div class="post-card__media post-card__media--video" aria-label="動画">
  <video controls preload="metadata"{poster_attr}>
    <source src="{video_url}">
    <a href="{html.escape(item.url, quote=True)}" target="_blank" rel="noopener noreferrer">動画を開く</a>
  </video>
</div>
""".strip()
    if images:
        overlay = '<span class="post-card__play-badge" aria-hidden="true">PLAY</span>'
        return render_image_grid(images[:1], extra_class="post-card__media--video-preview", overlay=overlay, link_url=item.url)
    return f"""
<div class="post-card__media post-card__media--video" aria-label="動画">
  <a class="post-card__video-placeholder" href="{html.escape(item.url, quote=True)}" target="_blank" rel="noopener noreferrer">VIDEO</a>
</div>
""".strip()


def render_image_grid(images: List[Dict[str, str]], extra_class: str = "", overlay: str = "", link_url: str = "") -> str:
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
        badge = overlay if index == 0 else ""
        more_badge = f'<span class="post-card__more">+{more}</span>' if more and index == len(visible) - 1 else ""
        content = f'<img src="{src}" alt="{alt}"{attrs} loading="{loading}" decoding="async">{badge}{more_badge}'
        if link_url:
            href = html.escape(link_url, quote=True)
            content = f'<a href="{href}" rel="noopener noreferrer" target="_blank">{content}</a>'
        image_html.append(f"<figure>{content}</figure>")
    classes = f'post-card__media post-card__media--count-{len(images)} {extra_class}'.strip()
    return f'<div class="{classes}">{"".join(image_html)}</div>'


def render_thumbnail_placeholder(item: SiteItem) -> str:
    source = html.escape(source_key_for(item))
    label = html.escape(item.source.upper() if item.source else "LINK")
    return f"""
<div class="post-card__thumb-placeholder" data-source-thumb="{source}" aria-hidden="true">
  <span>{label}</span>
</div>
""".strip()


def source_key_for(item: SiteItem) -> str:
    source = (item.source or "").lower()
    url = (item.url or "").lower()
    if "instagram.com" in url:
        return "instagram"
    if "x.com" in url or "twitter.com" in url or source in {"x", "twitter"}:
        return "x"
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "vimeo.com" in url:
        return "vimeo"
    if source:
        return source
    return "web"


def is_direct_video_url(url: str) -> bool:
    from src.site.metadata import is_direct_video_url as check

    return check(url)
