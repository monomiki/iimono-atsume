from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Iterable

from src.config import Settings, daily_page_url, public_base_url


def write_feed(public_dir: Path, settings: Settings, dates: Iterable[str]) -> None:
    items = []
    for run_date in sorted(set(dates), reverse=True)[:30]:
        url = daily_page_url(settings, run_date)
        items.append(
            f"""
  <item>
    <title>{html.escape(run_date)} AIデイリー収集</title>
    <link>{html.escape(url)}</link>
    <guid>{html.escape(url)}</guid>
  </item>""".rstrip()
        )
    feed = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
<channel>
  <title>AIデイリー収集</title>
  <link>{html.escape(public_base_url(settings))}</link>
  <description>Daily collected recommendations</description>
  <lastBuildDate>{datetime.utcnow().isoformat()}Z</lastBuildDate>
{chr(10).join(items)}
</channel>
</rss>
"""
    (public_dir / "feed.xml").write_text(feed, encoding="utf-8")


def write_sitemap(public_dir: Path, settings: Settings, dates: Iterable[str]) -> None:
    urls = [public_base_url(settings), f"{public_base_url(settings)}/favorites/"]
    urls.extend(daily_page_url(settings, date) for date in sorted(set(dates)))
    body = "\n".join(f"  <url><loc>{html.escape(url)}</loc></url>" for url in urls)
    (public_dir / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="utf-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n', encoding="utf-8")
    (public_dir / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n", encoding="utf-8")

