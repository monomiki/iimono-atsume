from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import quote

from src.config import Settings, daily_page_url
from src.site.cards import item_to_dict, site_item_from_recommendation
from src.site.feeds import write_feed, write_sitemap
from src.site.metadata import enrich_link_metadata
from src.site.pages import daily_body, index_body, render_page
from src.types import Recommendation, SiteItem


class StaticSiteBuilder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.public_dir = settings.public_dir
        self.data_dir = Path("data")

    def build_daily(self, run_date: str, recommendations: List[Recommendation], stats: Dict) -> Dict:
        items = [site_item_from_recommendation(rec, run_date) for rec in recommendations]
        return self.build_daily_from_items(run_date, items, stats)

    def build_daily_from_data(self, run_date: str) -> Dict:
        payload_path = self.data_dir / "daily" / f"{run_date}.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        items = [self._enrich_item(SiteItem(**item)) for item in payload.get("items", [])]
        stats = payload.get("stats", {})
        return self.build_daily_from_items(run_date, items, stats)

    def build_daily_from_items(self, run_date: str, items: List[SiteItem], stats: Dict) -> Dict:
        self._prepare()
        self._write_static_assets()
        self._write_data(run_date, items, stats)
        dates = self._known_dates()
        prev_date, next_date = self._neighbors(dates, run_date)
        daily_dir = self.public_dir / "daily" / run_date
        daily_dir.mkdir(parents=True, exist_ok=True)
        daily_html = render_page(
            f"{run_date} AIデイリー収集",
            daily_body(run_date, items, stats, self.settings, prev_date, next_date),
            self.settings,
        )
        (daily_dir / "index.html").write_text(daily_html, encoding="utf-8")
        (self.public_dir / "daily").mkdir(parents=True, exist_ok=True)
        (self.public_dir / "daily" / "index.html").write_text(render_page("Daily", index_body(dates, items, items, self.settings), self.settings), encoding="utf-8")
        self.build_index()
        return {"daily_path": str(daily_dir / "index.html"), "url": daily_page_url(self.settings, run_date), "items": len(items)}

    def build_index(self) -> None:
        self._prepare()
        self._write_static_assets()
        dates = self._known_dates()
        all_items = self._load_all_items()
        latest_items = [item for item in all_items if item.daily_page == (dates[-1] if dates else "")]
        (self.public_dir / "index.html").write_text(render_page("AIデイリー収集", index_body(dates, latest_items, all_items, self.settings), self.settings), encoding="utf-8")
        fav_dir = self.public_dir / "favorites"
        fav_dir.mkdir(parents=True, exist_ok=True)
        (fav_dir / "index.html").write_text(render_page("Favorites", self._favorites_body(all_items), self.settings), encoding="utf-8")
        self._write_preview()
        write_feed(self.public_dir, self.settings, dates)
        write_sitemap(self.public_dir, self.settings, dates)

    def _prepare(self) -> None:
        self.public_dir.mkdir(parents=True, exist_ok=True)
        (self.public_dir / "assets" / "css").mkdir(parents=True, exist_ok=True)
        (self.public_dir / "assets" / "js").mkdir(parents=True, exist_ok=True)
        (self.public_dir / "data" / "daily").mkdir(parents=True, exist_ok=True)
        (self.public_dir / "data" / "items").mkdir(parents=True, exist_ok=True)

    def _write_static_assets(self) -> None:
        shutil.copyfile(Path("site/static/css/main.css"), self.public_dir / "assets" / "css" / "main.css")
        shutil.copyfile(Path("site/static/js/favorites.js"), self.public_dir / "assets" / "js" / "favorites.js")
        shutil.copyfile(Path("site/static/js/masonry.js"), self.public_dir / "assets" / "js" / "masonry.js")

    def _write_data(self, run_date: str, items: List[SiteItem], stats: Dict) -> None:
        daily_payload = {"date": run_date, "stats": stats, "items": [item_to_dict(item) for item in items]}
        for base in (self.data_dir, self.public_dir / "data"):
            (base / "daily").mkdir(parents=True, exist_ok=True)
            (base / "items").mkdir(parents=True, exist_ok=True)
            (base / "daily" / f"{run_date}.json").write_text(json.dumps(daily_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            for item in items:
                (base / "items" / f"{item.item_id}.json").write_text(json.dumps(item_to_dict(item), ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_index_json()

    def _write_index_json(self) -> None:
        dates = self._known_dates()
        payload = {"dates": dates, "items": [item_to_dict(item) for item in self._load_all_items()]}
        for base in (self.data_dir, self.public_dir / "data"):
            base.mkdir(parents=True, exist_ok=True)
            (base / "index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _known_dates(self) -> List[str]:
        daily_dir = self.data_dir / "daily"
        dates = sorted(path.stem for path in daily_dir.glob("*.json"))
        return dates

    def _load_all_items(self) -> List[SiteItem]:
        items: List[SiteItem] = []
        for path in sorted((self.data_dir / "daily").glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            for item in data.get("items", []):
                items.append(SiteItem(**item))
        return items

    @staticmethod
    def _enrich_item(item: SiteItem) -> SiteItem:
        if item.image_url or item.images:
            return item
        metadata = enrich_link_metadata(item.url)
        image_url = metadata.get("image_url", "")
        video_url = metadata.get("video_url", "")
        if image_url:
            item.image_url = image_url
            item.images = [{"url": image_url, "alt": item.title}]
        if video_url and not item.video_url:
            item.video_url = video_url
        return item

    @staticmethod
    def _neighbors(dates: List[str], run_date: str) -> tuple[str, str]:
        if run_date not in dates:
            return "", ""
        idx = dates.index(run_date)
        prev_date = dates[idx - 1] if idx > 0 else ""
        next_date = dates[idx + 1] if idx + 1 < len(dates) else ""
        return prev_date, next_date

    def _favorites_body(self, items: List[SiteItem]) -> str:
        from src.site.pages import filter_bar, render_masonry
        from collections import Counter

        return f"""
<section class="hero compact-hero">
  <div><p class="eyebrow">AI DAILY COLLECTION</p><h1>Favorites</h1></div>
  {filter_bar(Counter(item.category for item in items), Counter(item.source for item in items), show_date=True)}
</section>
{render_masonry(items)}
"""

    def _write_preview(self) -> None:
        from datetime import datetime
        from src.site.pages import filter_bar, render_masonry, render_page
        from collections import Counter

        preview_items = preview_site_items()
        body = f"""
<section class="hero compact-hero">
  <div><p class="eyebrow">UI PREVIEW</p><h1>Masonry Embed Cards</h1><p class="date">短文、長文、横長画像、縦長画像、複数画像、動画、多言語を混在</p></div>
  {filter_bar(Counter(item.category for item in preview_items), Counter(item.source for item in preview_items), show_date=True)}
</section>
{render_masonry(preview_items)}
"""
        preview_dir = self.public_dir / "ui-preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        (preview_dir / "index.html").write_text(render_page("UI Preview", body, self.settings), encoding="utf-8")


def preview_site_items() -> List[SiteItem]:
    base = {
        "url": "https://example.com/post",
        "normalized_url": "https://example.com/post",
        "source": "web",
        "author": "preview",
        "published_at": "2026-07-22T07:00:00+09:00",
        "media_type": "article",
        "image_url": "",
        "video_url": "",
        "score": 84,
        "category": "design_graphic",
        "reasons": ["Discord Embed風カード確認", "メイソンリー再配置確認"],
        "novelty": ["UIプレビュー用データ"],
        "daily_page": "2026-07-22",
        "destination": "high",
        "discovery": False,
    }
    def image(label: str, width: int, height: int) -> Dict[str, str]:
        svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#15171b"/>
  <rect x="12" y="12" width="{width - 24}" height="{height - 24}" rx="10" fill="#202329" stroke="#00aff4" stroke-width="3"/>
  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#f2f3f5" font-family="Arial" font-size="32" font-weight="700">{label}</text>
</svg>
""".strip()
        return {"url": f"data:image/svg+xml,{quote(svg)}", "width": str(width), "height": str(height), "alt": label}
    cases = [
        ("short", "短い投稿", "本文だけの短いカードです。", [], "preview"),
        ("long", "長文カード", "これは長文カードです。" * 80, [], "long_writer"),
        ("wide", "横長画像", "横長画像をトリミングせず表示します。", [image("wide", 900, 420)], "wide_artist"),
        ("tall", "縦長画像", "縦長画像の高さがカードへ反映されます。", [image("tall", 500, 900)], "poster_ref"),
        ("square", "正方形画像", "正方形画像の確認。", [image("square", 700, 700)], "square_lab"),
        ("two", "画像2枚", "2枚の画像を横2列で表示します。", [image("two-a", 600, 700), image("two-b", 600, 500)], "duo"),
        ("three", "画像3枚", "大1枚と小2枚の配置です。", [image("three-a", 600, 850), image("three-b", 400, 400), image("three-c", 400, 520)], "triad"),
        ("four", "画像4枚", "2x2の複数画像カードです。", [image("four-a", 500, 500), image("four-b", 500, 640), image("four-c", 500, 420), image("four-d", 500, 500)], "gridder"),
        ("video", "動画", "直接動画URLがある場合はカード内で再生できます。", [image("poster", 900, 506)], "motion_id"),
        ("noavatar", "Avatarなし", "作者名がない状態でも崩れません。", [], ""),
        ("fav", "Favorite済み", "Favorite済み表示を確認します。", [image("fav", 600, 500)], "fav_user"),
        ("open", "推薦情報を開いたカード", "detailsを開いて高さが変わるケースです。", [], "ai_detail"),
        ("error", "読み込みエラー", "画像がなくてもカードは読めます。", [], "fallback"),
        ("jp", "日本語", "日本語の本文が読みやすいか確認します。余白を詰めすぎず、Discord Embedに近い密度です。", [], "日本語作者"),
        ("en", "English", "A compact English card with a readable body and footer metadata.", [], "english_ref"),
        ("ko", "한국어", "한국어 본문도 줄바꿈과 높이 계산이 자연스럽게 유지되는지 확인합니다.", [], "korean_ref"),
    ]
    items: List[SiteItem] = []
    for idx, (key, title, excerpt, images, author) in enumerate(cases):
        data = dict(base)
        data.update(
            {
                "item_id": f"preview_{key}",
                "title": title,
                "excerpt": excerpt,
                "author": author,
                "media_type": "video" if key == "video" else "article",
                "images": images,
                "video_url": "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4" if key == "video" else "",
                "score": max(52, 92 - idx * 2),
                "source": "youtube" if key == "video" else "x" if idx % 3 == 0 else "instagram" if idx % 3 == 1 else "web",
                "category": "vr_3d_tech" if idx % 4 == 0 else "design_graphic",
                "discovery": idx % 5 == 0,
                "destination": "high" if idx < 4 else "inbox",
            }
        )
        items.append(SiteItem(**data))
    return items
