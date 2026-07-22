from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

from src.config import Settings, site_path
from src.site.cards import render_link_card
from src.types import SiteItem


def render_page(title: str, body: str, settings: Settings) -> str:
    config = {
        "favoriteApiBaseUrl": settings.favorite_api_base_url,
        "allowedOrigin": settings.favorite_allowed_origin,
    }
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <link rel="stylesheet" href="{site_path(settings, "/assets/css/main.css")}">
  <script type="application/json" id="site-config">{html.escape(json.dumps(config), quote=False)}</script>
</head>
<body>
  <header class="site-header">
    <a class="brand" href="{site_path(settings, "/")}">AIデイリー収集</a>
    <nav><a href="{site_path(settings, "/daily/")}">Daily</a><a href="{site_path(settings, "/favorites/")}">Favorites</a><a href="{site_path(settings, "/feed.xml")}">RSS</a></nav>
  </header>
  <main>{body}</main>
  <script src="{site_path(settings, "/assets/js/favorites.js")}" defer></script>
  <script src="{site_path(settings, "/assets/js/masonry.js")}" defer></script>
</body>
</html>
"""


def daily_body(run_date: str, items: List[SiteItem], stats: Dict, settings: Settings, prev_date: str = "", next_date: str = "") -> str:
    category_counts = Counter(item.category for item in items)
    source_counts = Counter(item.source for item in items)
    prev_link = f'<a href="{site_path(settings, f"/daily/{prev_date}/")}">前日</a>' if prev_date else '<span>前日</span>'
    next_link = f'<a href="{site_path(settings, f"/daily/{next_date}/")}">翌日</a>' if next_date else '<span>翌日</span>'
    sorted_items = sorted(items, key=lambda item: (item.destination != "high" and item.score < 60, -item.score, not item.discovery, item.published_at), reverse=False)
    sections = [
        f"""
<section class="hero compact-hero">
  <div>
    <p class="eyebrow">AI DAILY COLLECTION</p>
    <h1>{html.escape(run_date.replace("-", "."))}</h1>
  </div>
  <div class="summary-grid">
    <span>{len(items)} ITEMS</span>
    <span>収集 {stats.get('candidates', len(items))}</span>
    <span>重複除外 {stats.get('duplicates', 0)}</span>
  </div>
  <div class="pager">{prev_link}<a href="{site_path(settings, "/")}">トップ</a>{next_link}</div>
  {filter_bar(category_counts, source_counts, show_date=False)}
</section>
""",
        render_masonry(sorted_items),
        render_count_section("カテゴリ別候補", category_counts),
        render_count_section("情報源別候補", source_counts),
    ]
    return "\n".join(sections)


def render_section(title: str, items: List[SiteItem]) -> str:
    cards = "\n".join(render_link_card(item) for item in items) or "<p>該当する候補はありません。</p>"
    return f'<section><h2>{html.escape(title)}</h2><div class="masonry-grid">{cards}</div></section>'


def render_masonry(items: List[SiteItem]) -> str:
    cards = "\n".join(render_link_card(item) for item in items) or "<p>該当する候補はありません。</p>"
    return f'<section aria-label="投稿一覧"><div class="masonry-grid" data-masonry>{cards}</div></section>'


def render_count_section(title: str, counts: Counter) -> str:
    rows = "".join(f"<li>{html.escape(key)} <span>{value}</span></li>" for key, value in counts.most_common())
    return f"<section><h2>{html.escape(title)}</h2><ul class=\"count-list\">{rows}</ul></section>"


def index_body(dates: List[str], latest_items: List[SiteItem], all_items: List[SiteItem], settings: Settings) -> str:
    category_counts = Counter(item.category for item in all_items)
    source_counts = Counter(item.source for item in all_items)
    latest_date = dates[-1] if dates else ""
    daily_links = "".join(f'<li><a href="{site_path(settings, f"/daily/{date}/")}">{date}</a></li>' for date in reversed(dates[-30:]))
    latest = render_masonry(latest_items[:12])
    return f"""
<section class="hero compact-hero">
  <div>
    <p class="eyebrow">AI DAILY COLLECTION</p>
    <h1>最新まとめ</h1>
    <p class="date">最終更新 {html.escape(latest_date or "未生成")}</p>
  </div>
  {filter_bar(category_counts, source_counts, show_date=True)}
</section>
{latest}
<section><h2>過去の日次まとめ</h2><ul class="archive-list">{daily_links}</ul></section>
{render_count_section("カテゴリ別の件数", category_counts)}
{render_count_section("情報源別の件数", source_counts)}
<section><h2>最近Favoriteしたコンテンツ</h2><p id="recent-favorites">各カードの星を付けると、FavoriteフィルターとFavorite優先ソートで使えます。</p></section>
"""


def filter_bar(category_counts: Counter, source_counts: Counter, show_date: bool) -> str:
    categories = "".join(f'<option value="{html.escape(key, quote=True)}">{html.escape(key)}</option>' for key in sorted(category_counts))
    sources = "".join(f'<option value="{html.escape(key, quote=True)}">{html.escape(key)}</option>' for key in sorted(source_counts))
    date_input = '<input id="date-filter" type="date" aria-label="日付">' if show_date else ""
    return f"""
<form class="filter-bar" data-filter-form>
  <div class="filter-segments" role="group" aria-label="表示フィルター">
    <button type="button" class="filter-chip is-active" data-filter-kind="all">すべて</button>
    <button type="button" class="filter-chip" data-filter-kind="high">高精度</button>
    <button type="button" class="filter-chip" data-filter-kind="discovery">新規発見</button>
    <button type="button" class="filter-chip" data-filter-kind="favorite">Favorite</button>
  </div>
  <select id="category-filter" aria-label="カテゴリ"><option value="">カテゴリ</option>{categories}</select>
  <select id="source-filter" aria-label="情報源"><option value="">情報源</option>{sources}</select>
  {date_input}
  <select id="sort-filter" aria-label="並び替え">
    <option value="score">推薦スコア順</option>
    <option value="favorite">Favorite優先</option>
    <option value="new">新着順</option>
  </select>
  <button type="button" class="density-toggle" data-density-toggle>標準表示</button>
</form>
""".strip()
