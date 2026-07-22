from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from src.config import Settings, daily_page_url
from src.site.cards import item_to_dict, site_item_from_recommendation
from src.site.feeds import write_feed, write_sitemap
from src.site.pages import daily_body, index_body, render_page
from src.types import Recommendation, SiteItem


class StaticSiteBuilder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.public_dir = settings.public_dir
        self.data_dir = Path("data")

    def build_daily(self, run_date: str, recommendations: List[Recommendation], stats: Dict) -> Dict:
        items = [site_item_from_recommendation(rec, run_date) for rec in recommendations]
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
        (self.public_dir / "daily" / "index.html").write_text(render_page("Daily", index_body(dates, items, items), self.settings), encoding="utf-8")
        self.build_index()
        return {"daily_path": str(daily_dir / "index.html"), "url": daily_page_url(self.settings, run_date), "items": len(items)}

    def build_index(self) -> None:
        self._prepare()
        dates = self._known_dates()
        all_items = self._load_all_items()
        latest_items = [item for item in all_items if item.daily_page == (dates[-1] if dates else "")]
        (self.public_dir / "index.html").write_text(render_page("AIデイリー収集", index_body(dates, latest_items, all_items), self.settings), encoding="utf-8")
        fav_dir = self.public_dir / "favorites"
        fav_dir.mkdir(parents=True, exist_ok=True)
        (fav_dir / "index.html").write_text(render_page("Favorites", "<section><h1>Favorites</h1><p id=\"favorites-list\">Favorite APIから読み込みます。</p></section>", self.settings), encoding="utf-8")
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
        for path in sorted((self.data_dir / "items").glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(SiteItem(**data))
        return items

    @staticmethod
    def _neighbors(dates: List[str], run_date: str) -> tuple[str, str]:
        if run_date not in dates:
            return "", ""
        idx = dates.index(run_date)
        prev_date = dates[idx - 1] if idx > 0 else ""
        next_date = dates[idx + 1] if idx + 1 < len(dates) else ""
        return prev_date, next_date

