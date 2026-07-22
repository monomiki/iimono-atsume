from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.config import ROOT, load_settings
from src.favorites.client import FavoriteService
from src.jobs.daily_job import DailyJob


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Raindrop preference recommender")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("analyze-library")
    sub.add_parser("build-profile")
    collect = sub.add_parser("collect")
    collect.add_argument("--source", choices=["x", "instagram", "web", "all"], default="all")
    sub.add_parser("recommend")
    daily = sub.add_parser("daily-run")
    daily.add_argument("--dry-run", action="store_true")
    daily.add_argument("--date", default="")
    build_site = sub.add_parser("build-site")
    build_site.add_argument("--date", default="")
    deploy_site = sub.add_parser("deploy-site")
    deploy_site.add_argument("--dry-run", action="store_true")
    notify = sub.add_parser("notify-discord")
    notify.add_argument("--date", required=True)
    notify.add_argument("--force", action="store_true")
    sub.add_parser("resend-pending-favorites")
    sub.add_parser("sync-web-favorites")
    sub.add_parser("feedback-sync")
    sub.add_parser("show-profile")
    args = parser.parse_args(argv)

    job = DailyJob(load_settings())
    if args.command in {"analyze-library", "build-profile"}:
        profile = job.build_profile()
        print(json.dumps({"categories": len(profile.get("categories", [])), "path": str(job.profiler.output_path)}, ensure_ascii=False, indent=2))
    elif args.command == "collect":
        candidates = job.collect(args.source)
        print(json.dumps([candidate.__dict__ for candidate in candidates], ensure_ascii=False, default=str, indent=2))
    elif args.command == "recommend":
        recommendations, duplicates, candidates_count = job.recommend()
        print(json.dumps({"candidates": candidates_count, "duplicates": len(duplicates), "recommendations": [r.__dict__ for r in recommendations]}, ensure_ascii=False, default=str, indent=2))
    elif args.command == "daily-run":
        print(json.dumps(job.run(dry_run=args.dry_run, run_date=args.date), ensure_ascii=False, indent=2))
    elif args.command == "build-site":
        print(json.dumps(job.build_site(args.date), ensure_ascii=False, indent=2))
    elif args.command == "deploy-site":
        print(json.dumps(job.deploy_site(dry_run=args.dry_run), ensure_ascii=False, indent=2))
    elif args.command == "notify-discord":
        print(json.dumps(job.notify_daily(args.date, force=args.force), ensure_ascii=False, indent=2))
    elif args.command == "resend-pending-favorites":
        print(json.dumps(FavoriteService(job.settings, job.db).resend_pending(), ensure_ascii=False, indent=2))
    elif args.command == "sync-web-favorites":
        print(json.dumps({"favorites": FavoriteService(job.settings, job.db).list_favorites()}, ensure_ascii=False, indent=2))
    elif args.command == "feedback-sync":
        print(json.dumps(job.feedback_sync(), ensure_ascii=False, indent=2))
    elif args.command == "show-profile":
        path = ROOT / "data" / "preference_profile.json"
        print(path.read_text(encoding="utf-8") if path.exists() else "{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
