from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.collectors.instagram_collector import InstagramCollector
from src.collectors.web_collector import WebCollector
from src.collectors.x_collector import XCollector
from src.config import DAILY_COLLECTIONS, ROOT, Settings, daily_page_url
from src.preference.feedback import FeedbackStore
from src.preference.profiler import PreferenceProfiler
from src.raindrop.client import RaindropClient, mock_bookmarks
from src.recommendation.classifier import CategoryClassifier
from src.recommendation.deduplicator import Deduplicator
from src.recommendation.diversity import apply_diversity
from src.recommendation.scorer import RecommendationScorer
from src.reporting.markdown_report import MarkdownReporter
from src.site.builder import StaticSiteBuilder
from src.site.deploy import SiteDeployer
from src.notifications.discord import DiscordNotifier
from src.storage.database import Database
from src.types import Bookmark, Candidate, Recommendation
from src.utils import normalize_url, utc_now_iso


class DailyJob:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.database_url)
        self.db.migrate()
        self.raindrop = RaindropClient(settings.raindrop_access_token)
        self.profiler = PreferenceProfiler(settings.profiles_dir / "preference_profile.json")

    def load_library(self) -> List[Bookmark]:
        if not self.raindrop.available:
            return mock_bookmarks()
        collections = self.raindrop.get_all_collections()
        bookmarks: List[Bookmark] = []
        for collection in collections:
            if collection.count <= 0:
                continue
            for bookmark in self.raindrop.get_raindrops(collection.id, max_items=250):
                bookmark.collection_title = collection.title
                bookmarks.append(bookmark)
        return bookmarks

    def build_profile(self) -> Dict:
        return self.profiler.build(self.load_library())

    def collect(self, source: str = "all") -> List[Candidate]:
        profile = self.profiler.load()
        collectors = {
            "x": XCollector(self.settings.x_bearer_token),
            "instagram": InstagramCollector(self.settings.instagram_access_token),
            "web": WebCollector(ROOT / "config" / "sources.yaml"),
        }
        selected = collectors.values() if source == "all" else [collectors[source]]
        candidates: List[Candidate] = []
        for collector in selected:
            try:
                candidates.extend(collector.collect(profile))
            except Exception:
                continue
        for candidate in candidates:
            candidate.url = normalize_url(candidate.url)
        return candidates

    def recommend(self) -> Tuple[List[Recommendation], List[Tuple[Candidate, str]], int]:
        bookmarks = self.load_library()
        profile = self.profiler.load()
        if not profile.get("categories"):
            profile = self.profiler.build(bookmarks)
        candidates = self.collect("all")
        deduplicator = Deduplicator(bookmarks)
        unique, duplicates = deduplicator.filter(candidates)
        classifier = CategoryClassifier()
        scorer = RecommendationScorer(FeedbackStore(self.db).score_adjustments())
        recommendations = [scorer.score(candidate, classifier.classify(candidate, profile), profile) for candidate in unique]
        recommendations = apply_diversity(recommendations, max_per_author=8, max_per_category=24)
        return recommendations, duplicates, len(candidates)

    def save_recommendations(self, recommendations: List[Recommendation], dry_run: bool) -> List[Recommendation]:
        selected = [rec for rec in recommendations if rec.score >= 45][: self.settings.max_daily_items]
        if dry_run or not self.raindrop.available:
            return selected
        collection_ids = self.raindrop.ensure_daily_collections(DAILY_COLLECTIONS)
        for rec in selected:
            destination_id = collection_ids.get(rec.destination, collection_ids["inbox"])
            self.raindrop.create_raindrop(rec, destination_id)
            self.db.execute(
                "INSERT OR REPLACE INTO saved_candidates(normalized_url, title, source, score, category, saved_at) VALUES (?, ?, ?, ?, ?, ?)",
                (normalize_url(rec.candidate.url), rec.candidate.title, rec.candidate.source, rec.score, rec.category, utc_now_iso()),
            )
        return selected

    def feedback_sync(self) -> Dict:
        if not self.raindrop.available:
            return {"synced": 0, "dry_run": True, "message": "Raindrop token is not configured"}
        collections = self.raindrop.get_all_collections()
        root_matches = [c for c in collections if c.title == DAILY_COLLECTIONS["root"]]
        if not root_matches:
            return {"synced": 0, "dry_run": False, "message": "AI daily collection does not exist yet"}
        root_id = sorted(root_matches, key=lambda c: (c.count, c.last_update), reverse=True)[0].id
        child_by_title = {c.title: c for c in collections if c.parent_id == root_id}
        actions = {
            DAILY_COLLECTIONS["high"]: ("positive_high_precision", 8.0),
            DAILY_COLLECTIONS["discovery"]: ("positive_discovery_kept", 4.0),
            DAILY_COLLECTIONS["negative"]: ("negative_not_interested", -12.0),
        }
        store = FeedbackStore(self.db)
        synced = 0
        for title, (action, delta) in actions.items():
            child = child_by_title.get(title)
            if not child:
                continue
            for bookmark in self.raindrop.get_raindrops(child.id, max_items=500):
                store.record(bookmark.url, action, bookmark.collection_title, delta)
                synced += 1
        return {"synced": synced, "dry_run": False}

    def run(self, dry_run: bool = False, run_date: str = "", skip_deploy: bool = False) -> Dict:
        profile = self.build_profile()
        recommendations, duplicates, candidates_count = self.recommend()
        effective_dry_run = dry_run or self.settings.dry_run
        saved = self.save_recommendations(recommendations, effective_dry_run)
        run_date = run_date or datetime.now().strftime("%Y-%m-%d")
        report_path = MarkdownReporter(self.settings.reports_dir).write(run_date, candidates_count, duplicates, recommendations, saved)
        stats = {"candidates": candidates_count, "duplicates": len(duplicates), "evaluated": len(recommendations), "saved": len(saved)}
        site_result = StaticSiteBuilder(self.settings).build_daily(run_date, saved, stats)
        deploy_result = {"status": "skipped", "reason": "skip_deploy"} if skip_deploy else SiteDeployer(self.settings).deploy(effective_dry_run)
        notify_result = {"status": "skipped", "reason": "dry_run_or_deploy_not_confirmed"}
        if not effective_dry_run and deploy_result.get("status") == "deployed":
            verify = SiteDeployer.verify(site_result["url"])
            if verify.get("status") == "ok":
                notify_result = self.notify_daily(run_date, site_result["url"], saved, force=False)
        self.db.execute(
            "INSERT OR REPLACE INTO daily_runs(run_date, candidates, duplicates, evaluated, saved, report_path) VALUES (?, ?, ?, ?, ?, ?)",
            (run_date, candidates_count, len(duplicates), len(recommendations), len(saved), str(report_path)),
        )
        return {
            "profile": profile,
            "candidates": candidates_count,
            "duplicates": len(duplicates),
            "evaluated": len(recommendations),
            "saved": len(saved),
            "report_path": str(report_path),
            "site": site_result,
            "deploy": deploy_result,
            "discord": notify_result,
            "dry_run": effective_dry_run or not self.raindrop.available,
        }

    def build_site(self, run_date: str = "") -> Dict:
        date = run_date or datetime.now().strftime("%Y-%m-%d")
        recommendations, duplicates, candidates_count = self.recommend()
        saved = [rec for rec in recommendations if rec.score >= 45][: self.settings.max_daily_items]
        stats = {"candidates": candidates_count, "duplicates": len(duplicates), "evaluated": len(recommendations), "saved": len(saved)}
        return StaticSiteBuilder(self.settings).build_daily(date, saved, stats)

    def deploy_site(self, dry_run: bool = False) -> Dict:
        return SiteDeployer(self.settings).deploy(dry_run)

    def notify_daily(self, run_date: str, page_url: str = "", recommendations: Optional[List[Recommendation]] = None, force: bool = False) -> Dict:
        recs = recommendations or []
        data_items = []
        if not recs:
            payload_path = ROOT / "data" / "daily" / f"{run_date}.json"
            if payload_path.exists():
                payload = json.loads(payload_path.read_text(encoding="utf-8"))
                data_items = payload.get("items", [])
        category_counts = Counter(rec.category for rec in recs) if recs else Counter(item.get("category", "") for item in data_items)
        payload = {
            "date": run_date,
            "page_url": page_url or daily_page_url(self.settings, run_date),
            "total": len(recs) if recs else len(data_items),
            "high": len([rec for rec in recs if rec.destination == "high" or rec.score >= 60]) if recs else len([item for item in data_items if item.get("destination") == "high" or int(item.get("score", 0)) >= 60]),
            "discovery": len([rec for rec in recs if rec.candidate.discovery]) if recs else len([item for item in data_items if item.get("discovery")]),
            "top_category": category_counts.most_common(1)[0][0] if category_counts else "未集計",
            "top_score": max([rec.score for rec in recs], default="-") if recs else max([int(item.get("score", 0)) for item in data_items], default="-"),
            "force": force,
        }
        return DiscordNotifier(self.settings, self.db).send_daily(payload)
