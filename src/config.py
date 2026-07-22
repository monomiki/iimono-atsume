from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    raindrop_access_token: str
    x_bearer_token: str
    instagram_access_token: str
    openai_api_key: str
    database_url: str
    timezone: str
    daily_run_time: str
    max_daily_items: int
    dry_run: bool
    reports_dir: Path
    profiles_dir: Path
    public_site_domain: str
    public_site_base_url: str
    public_site_path_prefix: str
    public_dir: Path
    github_repository: str
    github_default_branch: str
    github_pages_branch: str
    github_token: str
    discord_bot_token: str
    discord_guild_id: str
    discord_daily_channel_id: str
    discord_clipboard_channel_id: str
    discord_daily_webhook_url: str
    discord_clipboard_webhook_url: str
    favorite_api_base_url: str
    favorite_api_secret: str
    favorite_auth_mode: str
    favorite_allowed_origin: str
    favorite_database_url: str
    cloudflare_account_id: str
    cloudflare_api_token: str
    cloudflare_worker_name: str
    cloudflare_d1_database_id: str
    cloudflare_kv_namespace_id: str


def load_settings() -> Settings:
    _load_dotenv()
    return Settings(
        raindrop_access_token=os.getenv("RAINDROP_ACCESS_TOKEN", ""),
        x_bearer_token=os.getenv("X_BEARER_TOKEN", ""),
        instagram_access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/recommendations.db"),
        timezone=os.getenv("TIMEZONE", "Asia/Tokyo"),
        daily_run_time=os.getenv("DAILY_RUN_TIME", "07:00"),
        max_daily_items=int(os.getenv("MAX_DAILY_ITEMS", "30")),
        dry_run=os.getenv("DRY_RUN", "true").lower() in {"1", "true", "yes", "on"},
        reports_dir=ROOT / "reports",
        profiles_dir=ROOT / "data",
        public_site_domain=os.getenv("PUBLIC_SITE_DOMAIN", ""),
        public_site_base_url=os.getenv("PUBLIC_SITE_BASE_URL", ""),
        public_site_path_prefix=os.getenv("PUBLIC_SITE_PATH_PREFIX", "/daily"),
        public_dir=ROOT / "public",
        github_repository=os.getenv("GITHUB_REPOSITORY", "") or infer_github_repository(),
        github_default_branch=os.getenv("GITHUB_DEFAULT_BRANCH", "main"),
        github_pages_branch=os.getenv("GITHUB_PAGES_BRANCH", "gh-pages"),
        github_token=os.getenv("GITHUB_TOKEN", ""),
        discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
        discord_guild_id=os.getenv("DISCORD_GUILD_ID", ""),
        discord_daily_channel_id=os.getenv("DISCORD_DAILY_CHANNEL_ID", ""),
        discord_clipboard_channel_id=os.getenv("DISCORD_CLIPBOARD_CHANNEL_ID", ""),
        discord_daily_webhook_url=os.getenv("DISCORD_DAILY_WEBHOOK_URL", ""),
        discord_clipboard_webhook_url=os.getenv("DISCORD_CLIPBOARD_WEBHOOK_URL", ""),
        favorite_api_base_url=os.getenv("FAVORITE_API_BASE_URL", ""),
        favorite_api_secret=os.getenv("FAVORITE_API_SECRET", ""),
        favorite_auth_mode=os.getenv("FAVORITE_AUTH_MODE", "shared-passcode"),
        favorite_allowed_origin=os.getenv("FAVORITE_ALLOWED_ORIGIN", ""),
        favorite_database_url=os.getenv("FAVORITE_DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///data/recommendations.db")),
        cloudflare_account_id=os.getenv("CLOUDFLARE_ACCOUNT_ID", ""),
        cloudflare_api_token=os.getenv("CLOUDFLARE_API_TOKEN", ""),
        cloudflare_worker_name=os.getenv("CLOUDFLARE_WORKER_NAME", ""),
        cloudflare_d1_database_id=os.getenv("CLOUDFLARE_D1_DATABASE_ID", ""),
        cloudflare_kv_namespace_id=os.getenv("CLOUDFLARE_KV_NAMESPACE_ID", ""),
    )


def public_base_url(settings: Settings) -> str:
    base = settings.public_site_base_url.strip().rstrip("/")
    if base:
        return base
    domain = settings.public_site_domain.strip()
    if domain:
        return f"https://{domain}"
    return "http://localhost:8000"


def daily_page_url(settings: Settings, run_date: str) -> str:
    prefix = "/" + settings.public_site_path_prefix.strip("/")
    if prefix == "/":
        prefix = "/daily"
    return f"{public_base_url(settings)}{prefix}/{run_date}/"


def site_origin(settings: Settings) -> Optional[str]:
    parsed = urlparse(public_base_url(settings))
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return None


def infer_github_repository() -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    remote = result.stdout.strip()
    if remote.startswith("git@github.com:"):
        repo = remote.removeprefix("git@github.com:").removesuffix(".git")
        return repo
    if "github.com/" in remote:
        repo = remote.split("github.com/", 1)[1].removesuffix(".git")
        return repo
    return ""


INTEREST_CATEGORIES: Dict[str, List[str]] = {
    "design_graphic": [
        "デザイン-リファレンス", "🟥gra_main", "🟨gra_otaku", "🟩gra_paper",
        "🔴logo_main", "🟡logo_otaku", "🟣logo_motion", "😤typo", "😡font",
        "🧰pd-商品", "🔨pd-いいitem", "🔧pd-matome", "🌙art", "🎈kazari", "良い物体",
    ],
    "illustration_video_space": [
        "リファレンス", "✊イラスト_chara-goods", "🖼イラスト_実用参考", "🍁イラスト_風景シチュ",
        "🎨イラスト_その他", "🎥映像", "🌱映像-作品など", "🤖gif", "✨アイデア",
        "🏢建築", "📦空間", "📸写真", "⛄写真合成", "😇仮想", "💢創作参考", "🌐web", "🪡服飾",
    ],
    "vr_3d_tech": [
        "VRCHAT", "🌍ワールド", "💞参考", "🍬アイテム・ギミック", "👍tips",
        "🎍改変tips", "👀気になる", "👗服", "💻3d", "🏭3dプリンター",
        "🧠ai", "🚧ガジェット情報", "📍アプリ_tips",
    ],
    "culture_places": ["📆展示・イベント", "🗼よさげスポット情報", "🌳場所", "📗本", "🙌記事-サイト", "📕漫画", "🎵音楽", "👄言葉、文章、概念", "📹動画"],
    "life_product": ["💺家具", "👚ファッション", "🍙料理", "🍰おかし", "🔑キーボード", "👐健康・生活", "🏠いい感じの部屋", "💡欲しいがじぇっと"],
    "fun_sensory": ["⭐なんか良いなとなったもの", "🐈ねこいぬアニマル", "💥おもしろどうが", "❓なぞ"],
}

EXCLUDED_COLLECTION_NAMES = {
    "Trash", "アーカイブ", "moderator-only", "保留", "📎クリップボード", "デフォ",
}

DAILY_COLLECTIONS = {
    "root": "🤖 AIデイリー収集",
    "inbox": "📥 未確認",
    "high": "⭐ 高精度",
    "discovery": "🧭 新規発見",
    "negative": "🚫 興味なし",
}
