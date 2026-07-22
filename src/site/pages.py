from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List

from src.config import Settings, daily_page_url
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
  <link rel="stylesheet" href="/assets/css/main.css">
  <script type="application/json" id="site-config">{html.escape(json.dumps(config), quote=False)}</script>
</head>
<body>
  <header class="site-header">
    <a class="brand" href="/">AIデイリー収集</a>
    <nav><a href="/daily/">Daily</a><a href="/favorites/">Favorites</a><a href="/feed.xml">RSS</a></nav>
  </header>
  <main>{body}</main>
  <script src="/assets/js/favorites.js" defer></script>
</body>
</html>
"""


def daily_body(run_date: str, items: List[SiteItem], stats: Dict, settings: Settings, prev_date: str = "", next_date: str = "") -> str:
    recommended = [item for item in items if item.destination == "high" or item.score >= 60]
    normal = [item for item in items if item not in recommended and not item.discovery]
    discoveries = [item for item in items if item.discovery]
    category_counts = Counter(item.category for item in items)
    source_counts = Counter(item.source for item in items)
    prev_link = f'<a href="/daily/{prev_date}/">前日</a>' if prev_date else '<span>前日</span>'
    next_link = f'<a href="/daily/{next_date}/">翌日</a>' if next_date else '<span>翌日</span>'
    sections = [
        f"""
<section class="hero">
  <p class="date">{html.escape(run_date)}</p>
  <h1>今日の情報収集まとめ</h1>
  <div class="summary-grid">
    <span>収集 {stats.get('candidates', len(items))}</span>
    <span>保存候補 {len(items)}</span>
    <span>重複除外 {stats.get('duplicates', 0)}</span>
  </div>
  <div class="pager">{prev_link}<a href="/">トップ</a>{next_link}</div>
</section>
""",
        render_section("特におすすめ", recommended),
        render_section("通常候補", normal),
        render_section("新規発見", discoveries),
        render_count_section("カテゴリ別候補", category_counts),
        render_count_section("情報源別候補", source_counts),
    ]
    return "\n".join(sections)


def render_section(title: str, items: List[SiteItem]) -> str:
    cards = "\n".join(render_link_card(item) for item in items) or "<p>該当する候補はありません。</p>"
    return f'<section><h2>{html.escape(title)}</h2><div class="card-grid">{cards}</div></section>'


def render_count_section(title: str, counts: Counter) -> str:
    rows = "".join(f"<li>{html.escape(key)} <span>{value}</span></li>" for key, value in counts.most_common())
    return f"<section><h2>{html.escape(title)}</h2><ul class=\"count-list\">{rows}</ul></section>"


def index_body(dates: List[str], latest_items: List[SiteItem], all_items: List[SiteItem]) -> str:
    category_counts = Counter(item.category for item in all_items)
    source_counts = Counter(item.source for item in all_items)
    latest_date = dates[-1] if dates else ""
    daily_links = "".join(f'<li><a href="/daily/{date}/">{date}</a></li>' for date in reversed(dates[-30:]))
    latest = render_section("最新の日次まとめ", latest_items[:6])
    return f"""
<section class="hero">
  <p class="date">最終更新 {html.escape(latest_date or "未生成")}</p>
  <h1>AIデイリー収集</h1>
  <div class="filters">
    <input id="search" type="search" placeholder="日付・カテゴリ・情報源で絞り込み">
    <label><input id="favorites-only" type="checkbox"> Favorite済み</label>
  </div>
</section>
{latest}
<section><h2>過去の日次まとめ</h2><ul class="archive-list">{daily_links}</ul></section>
{render_count_section("カテゴリ別の件数", category_counts)}
{render_count_section("情報源別の件数", source_counts)}
<section><h2>最近Favoriteしたコンテンツ</h2><p id="recent-favorites">Favorite APIから読み込みます。</p></section>
"""

