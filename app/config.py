from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    app_env: str = "local"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_url: str = "sqlite:///./cocktail_index.db"
    creator_config_path: Path = BASE_DIR / "config" / "creators.yml"
    media_dir: Path = BASE_DIR / "data" / "media"
    instagram_public_backfill_max_posts: int = 120
    instagram_public_incremental_max_posts: int = 30
    instagram_public_request_delay_seconds: float = 1.5


def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./cocktail_index.db"),
        creator_config_path=Path(
            os.getenv("CREATOR_CONFIG_PATH", str(BASE_DIR / "config" / "creators.yml"))
        ),
        media_dir=Path(os.getenv("MEDIA_DIR", str(BASE_DIR / "data" / "media"))),
        instagram_public_backfill_max_posts=int(os.getenv("INSTAGRAM_PUBLIC_BACKFILL_MAX_POSTS", "120")),
        instagram_public_incremental_max_posts=int(os.getenv("INSTAGRAM_PUBLIC_INCREMENTAL_MAX_POSTS", "30")),
        instagram_public_request_delay_seconds=float(os.getenv("INSTAGRAM_PUBLIC_REQUEST_DELAY_SECONDS", "1.5")),
    )
