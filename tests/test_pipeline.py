from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import io
import json
import urllib.error

from src.jobs.daily_job import DailyJob
from src.raindrop.client import RaindropClient, mock_bookmarks
from src.recommendation.deduplicator import Deduplicator
from src.recommendation.diversity import apply_diversity
from src.recommendation.scorer import RecommendationScorer
from src.storage.database import Database
from src.types import Candidate, Collection
from src.utils import normalize_url, post_identity
from src.config import Settings
from src.config import daily_page_url
from src.favorites.client import FavoriteService
from src.notifications.discord import DiscordNotifier
from src.site.builder import StaticSiteBuilder
from src.site.cards import render_link_card, site_item_from_recommendation
from src.site.metadata import enrich_link_metadata


def make_settings(tmp: str = "", **overrides):
    base = Path(tmp) if tmp else Path(".")
    values = dict(
        raindrop_access_token="",
        x_bearer_token="",
        instagram_access_token="",
        openai_api_key="",
        database_url=f"sqlite:///{base / 'db.sqlite'}" if tmp else "sqlite:///data/test.sqlite",
        timezone="Asia/Tokyo",
        daily_run_time="07:00",
        max_daily_items=30,
        dry_run=True,
        reports_dir=base / "reports",
        profiles_dir=base,
        public_site_domain="",
        public_site_base_url="https://example.com",
        public_site_path_prefix="/daily",
        public_dir=base / "public",
        github_repository="",
        github_default_branch="main",
        github_pages_branch="gh-pages",
        github_token="",
        discord_bot_token="",
        discord_guild_id="",
        discord_daily_channel_id="",
        discord_clipboard_channel_id="",
        discord_daily_webhook_url="",
        discord_clipboard_webhook_url="",
        favorite_api_base_url="",
        favorite_api_secret="secret",
        favorite_auth_mode="shared-passcode",
        favorite_allowed_origin="",
        favorite_database_url="",
        cloudflare_account_id="",
        cloudflare_api_token="",
        cloudflare_worker_name="",
        cloudflare_d1_database_id="",
        cloudflare_kv_namespace_id="",
    )
    values.update(overrides)
    return Settings(**values)


class PipelineTests(unittest.TestCase):
    def test_resolves_collection_by_name_and_prefers_active_duplicate(self):
        client = RaindropClient()
        collections = [
            Collection(1, "🟣logo_motion", count=2, parent_id=10, last_update="2024-01-01"),
            Collection(2, "🟣logo_motion", count=9, parent_id=10, last_update="2026-01-01"),
        ]
        self.assertEqual(client.resolve_collection_id(collections, "🟣logo_motion", parent_id=10), 2)

    def test_normalizes_x_urls(self):
        self.assertEqual(
            normalize_url("https://fxtwitter.com/user/status/123?utm_source=a"),
            "https://x.com/user/status/123",
        )

    def test_normalizes_instagram_urls(self):
        self.assertEqual(
            normalize_url("https://instagram.com/p/ABC123/?igshid=xyz&utm_source=x"),
            "https://www.instagram.com/p/ABC123",
        )

    def test_detects_mirror_post_identity(self):
        self.assertEqual(
            post_identity("https://vxtwitter.com/name/status/555"),
            post_identity("https://x.com/name/status/555?utm_campaign=a"),
        )

    def test_excludes_existing_bookmarks(self):
        dedup = Deduplicator(mock_bookmarks())
        kept, removed = dedup.filter([Candidate("same", "https://example.com/type-poster", "web")])
        self.assertEqual(kept, [])
        self.assertEqual(len(removed), 1)

    def test_scoring_is_reproducible(self):
        profile = {"categories": [{"category": "design_graphic", "positive_features": ["typography", "motion"], "preferred_domains": []}]}
        candidate = Candidate("Motion typography", "https://x.com/a/status/1", "x", text="typography motion identity", media_type="video")
        scorer = RecommendationScorer()
        self.assertEqual(scorer.score(candidate, "design_graphic", profile).score, scorer.score(candidate, "design_graphic", profile).score)

    def test_limits_same_author(self):
        profile = {"categories": [{"category": "design_graphic", "positive_features": ["typography"], "preferred_domains": []}]}
        scorer = RecommendationScorer()
        recs = [
            scorer.score(Candidate(f"item {i}", f"https://x.com/a/status/{i}", "x", author="a", text="typography"), "design_graphic", profile)
            for i in range(5)
        ]
        self.assertEqual(len(apply_diversity(recs, max_per_author=3)), 3)

    def test_empty_api_like_response_does_not_stop(self):
        dedup = Deduplicator([])
        kept, removed = dedup.filter([])
        self.assertEqual(kept, [])
        self.assertEqual(removed, [])

    def test_database_feedback_adjusts_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(f"sqlite:///{tmp}/db.sqlite")
            db.migrate()
            db.execute(
                "INSERT INTO feedback(url, normalized_url, action, category, score_delta, observed_at) VALUES (?, ?, ?, ?, ?, ?)",
                ("https://example.com/a", "https://example.com/a", "good", "design_graphic", 10, "now"),
            )
            rows = db.query("SELECT SUM(score_delta) AS delta FROM feedback")
            self.assertEqual(rows[0]["delta"], 10)

    def test_health_info_does_not_enter_high_precision(self):
        profile = {"categories": [{"category": "life_product", "positive_features": ["health"], "preferred_domains": []}]}
        rec = RecommendationScorer().score(
            Candidate("Miracle posture", "https://health.example/a", "web", text="miracle cure health hack no evidence"),
            "life_product",
            profile,
        )
        self.assertNotEqual(rec.destination, "high")
        self.assertLessEqual(rec.score, 69)

    def test_dry_run_does_not_save_to_raindrop_and_completes(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(tmp)
            result = DailyJob(settings).run(dry_run=True)
            self.assertTrue(result["dry_run"])
            self.assertTrue(Path(result["report_path"]).exists())

    def test_dry_run_skips_raindrop_save_even_when_client_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(tmp)
            job = DailyJob(settings)
            called = {"count": 0}

            class FakeRaindrop(RaindropClient):
                @property
                def available(self):
                    return True

                def ensure_daily_collections(self, names):
                    return {"root": 1, "inbox": 2, "high": 3, "discovery": 4, "negative": 5}

                def create_raindrop(self, recommendation, collection_id):
                    called["count"] += 1

                def get_all_collections(self):
                    return []

            job.raindrop = FakeRaindrop("token")
            recs, _, _ = job.recommend()
            job.save_recommendations(recs, dry_run=True)
            self.assertEqual(called["count"], 0)

    def test_raindrop_rate_limit_retries_then_succeeds(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"items":[]}'

        calls = {"count": 0}

        def fake_urlopen(request, timeout):
            calls["count"] += 1
            if calls["count"] == 1:
                raise urllib.error.HTTPError(request.full_url, 429, "rate limited", {}, io.BytesIO(b"rate limited"))
            return FakeResponse()

        with patch("time.sleep", lambda seconds: None), patch("urllib.request.urlopen", fake_urlopen):
            self.assertEqual(RaindropClient("token", retries=2).get_root_collections(), [])
        self.assertEqual(calls["count"], 2)

    def test_static_daily_page_and_link_card_are_generated(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(tmp, public_site_domain="イキモノ.コム", public_site_base_url="https://イキモノ.コム", discord_daily_webhook_url="https://discord.example/daily-secret", discord_clipboard_webhook_url="https://discord.example/clip-secret", favorite_api_base_url="https://favorite.example", favorite_allowed_origin="https://イキモノ.コム")
            job = DailyJob(settings)
            recs, _, _ = job.recommend()
            result = StaticSiteBuilder(settings).build_daily("2026-07-22", recs[:2], {"candidates": 2, "duplicates": 0})
            html = Path(result["daily_path"]).read_text(encoding="utf-8")
            self.assertIn("post-card link-card", html)
            self.assertNotIn("favorite-button__label", html)
            self.assertNotIn("元投稿を見る", html)
            self.assertIn("masonry-grid", html)
            self.assertNotIn("discord.example", html)
            self.assertNotIn("secret", html)
            css = (settings.public_dir / "assets" / "css" / "main.css").read_text(encoding="utf-8")
            js = (settings.public_dir / "assets" / "js" / "masonry.js").read_text(encoding="utf-8")
            self.assertIn("@media (max-width: 520px)", css)
            self.assertIn("ResizeObserver", js)
            self.assertNotIn("discord.example", js)

    def test_link_card_contains_candidate_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(tmp)
            job = DailyJob(settings)
            recs, _, _ = job.recommend()
            item = site_item_from_recommendation(recs[0], "2026-07-22")
            card = render_link_card(item)
            self.assertIn(item.title, card)
            self.assertIn(item.item_id, card)
            self.assertIn("post-card__author", card)
            self.assertIn("post-card__details", card)
            self.assertIn(f'<a class="post-card__display-name" href="{item.url}"', card)
            self.assertIn(f'<h3 class="post-card__title"><a href="{item.url}"', card)
            self.assertNotIn("元投稿を見る", card)

    def test_link_card_renders_thumbnail_video_and_source_accent_key(self):
        item = site_item_from_recommendation(
            RecommendationScorer().score(
                Candidate(
                    "Playable sample",
                    "https://youtu.be/example",
                    "youtube",
                    text="motion identity",
                    media_type="video",
                    image_url="https://cdn.example/poster.jpg",
                    video_url="https://cdn.example/video.mp4",
                ),
                "design_graphic",
                {"categories": []},
            ),
            "2026-07-22",
        )
        card = render_link_card(item)
        self.assertIn('data-source-key="youtube"', card)
        self.assertIn('post-card__avatar post-card__avatar--image', card)
        self.assertIn('<img src="https://cdn.example/poster.jpg"', card)
        self.assertIn("<video controls", card)
        self.assertIn("poster=", card)
        self.assertIn("https://cdn.example/video.mp4", card)

    def test_image_thumbnail_links_to_source_and_favorite_is_star_only(self):
        item = site_item_from_recommendation(
            RecommendationScorer().score(
                Candidate(
                    "Image sample",
                    "https://example.com/post",
                    "web",
                    text="typography",
                    media_type="image",
                    image_url="https://cdn.example/thumb.jpg",
                ),
                "design_graphic",
                {"categories": []},
            ),
            "2026-07-22",
        )
        card = render_link_card(item)
        self.assertIn('<a href="https://example.com/post" rel="noopener noreferrer" target="_blank"><img src="https://cdn.example/thumb.jpg"', card)
        self.assertIn('aria-label="Favorite Image sample"', card)
        self.assertIn('<span aria-hidden="true">☆</span>', card)
        self.assertNotIn("Favorite</span>", card)

    def test_daily_page_url_uses_configured_domain(self):
        settings = make_settings(public_site_domain="イキモノ.コム", public_site_base_url="https://イキモノ.コム")
        self.assertEqual(daily_page_url(settings, "2026-07-22"), "https://イキモノ.コム/daily/2026-07-22/")

    def test_same_day_discord_notification_is_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(tmp)
            job = DailyJob(settings)
            first = job.notify_daily("2026-07-22", "https://example.com/daily/2026-07-22/")
            second = job.notify_daily("2026-07-22", "https://example.com/daily/2026-07-22/")
            self.assertEqual(first["status"], "skipped")
            self.assertEqual(second["reason"], "already_notified")

    def test_favorite_registers_once_and_records_pending_when_discord_unconfigured(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(tmp)
            job = DailyJob(settings)
            recs, _, _ = job.recommend()
            item = site_item_from_recommendation(recs[0], "2026-07-22")
            Path("data/items").mkdir(parents=True, exist_ok=True)
            (Path("data/items") / f"{item.item_id}.json").write_text(json.dumps(item.__dict__, ensure_ascii=False), encoding="utf-8")
            service = FavoriteService(settings, job.db)
            first = service.favorite(item.item_id, "2026-07-22", authenticated=True)
            second = service.favorite(item.item_id, "2026-07-22", authenticated=True)
            self.assertEqual(first["discord_status"], "pending")
            self.assertEqual(second["status"], "already_favorited")
            self.assertEqual(service.favorite("missing", "2026-07-22", authenticated=True)["status"], "not_found")
            self.assertEqual(service.favorite(item.item_id, "2026-07-22", authenticated=False)["status"], "forbidden")
            self.assertEqual(service.resend_pending()["sent"], 0)
            rows = job.db.query("SELECT * FROM feedback WHERE action = 'web_favorite'")
            self.assertEqual(len(rows), 1)

    def test_favorite_discord_uses_daily_webhook_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(
                tmp,
                discord_daily_webhook_url="https://discord.example/daily",
                discord_clipboard_webhook_url="https://discord.example/clipboard",
            )
            db = Database(settings.database_url)
            db.migrate()
            seen = {}

            def fake_post(webhook_url, body):
                seen["webhook_url"] = webhook_url
                seen["body"] = body
                return {"status": "sent"}

            with patch.object(DiscordNotifier, "_post", staticmethod(fake_post)):
                result = DiscordNotifier(settings, db).send_favorite(
                    {
                        "title": "Favorite item",
                        "url": "https://example.com/item",
                        "daily_url": "https://example.com/daily/2026-07-22/",
                    }
                )

            self.assertEqual(result["status"], "sent")
            self.assertEqual(seen["webhook_url"], "https://discord.example/daily")

    def test_masonry_css_breakpoints_and_fallback_are_present(self):
        css = Path("site/static/css/main.css").read_text(encoding="utf-8")
        self.assertIn("grid-template-columns: repeat(auto-fill", css)
        self.assertIn("grid-auto-rows: var(--masonry-row)", css)
        self.assertIn("--card-min: 280px", css)
        self.assertIn("@media (max-width: 520px)", css)
        self.assertIn("@media (min-width: 1180px)", css)
        self.assertIn("@media (min-width: 1540px)", css)
        self.assertNotIn("min-height: 100%", css)
        self.assertIn('data-source-key="instagram"', css)
        self.assertIn("post-card__thumb-placeholder", css)
        self.assertIn(".post-card__media video", css)

    def test_masonry_js_reacts_to_layout_changing_events(self):
        js = Path("site/static/js/masonry.js").read_text(encoding="utf-8")
        self.assertIn("ResizeObserver", js)
        self.assertIn("MutationObserver", js)
        self.assertIn("favorite-state-change", js)
        self.assertIn("details", js)
        self.assertIn("load", js)
        self.assertIn("gridRowEnd", js)

    def test_ui_preview_page_contains_mixed_masonry_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = make_settings(tmp)
            job = DailyJob(settings)
            recs, _, _ = job.recommend()
            StaticSiteBuilder(settings).build_daily("2026-07-22", recs[:2], {"candidates": 2, "duplicates": 0})
            html = (settings.public_dir / "ui-preview" / "index.html").read_text(encoding="utf-8")
            for label in ["長文カード", "横長画像", "縦長画像", "画像2枚", "動画", "한국어"]:
                self.assertIn(label, html)
            self.assertIn("<video controls", html)

    def test_metadata_enrichment_reads_open_graph_media(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            @property
            def headers(self):
                return {"content-type": "text/html; charset=utf-8"}

            def read(self, size=-1):
                return b'<meta property="og:image" content="/thumb.jpg"><meta property="og:video" content="https://cdn.example/movie.mp4">'

            def geturl(self):
                return "https://example.com/post"

        with patch("urllib.request.urlopen", lambda request, timeout: FakeResponse()):
            media = enrich_link_metadata("https://example.com/post")
        self.assertEqual(media["image_url"], "https://example.com/thumb.jpg")
        self.assertEqual(media["video_url"], "https://cdn.example/movie.mp4")


if __name__ == "__main__":
    unittest.main()
