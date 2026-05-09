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
    instagram_session_state_path: Path = Path.home() / ".config" / "cocktail-index" / "instagram-storage-state.json"
    instagram_backfill_max_posts: int = 120
    instagram_incremental_max_posts: int = 30
    instagram_unchanged_stop_count: int = 12


def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./cocktail_index.db"),
        creator_config_path=Path(
            os.getenv("CREATOR_CONFIG_PATH", str(BASE_DIR / "config" / "creators.yml"))
        ),
        instagram_session_state_path=Path(
            os.getenv(
                "INSTAGRAM_SESSION_STATE_PATH",
                str(Path.home() / ".config" / "cocktail-index" / "instagram-storage-state.json"),
            )
        ),
        instagram_backfill_max_posts=int(os.getenv("INSTAGRAM_BACKFILL_MAX_POSTS", "120")),
        instagram_incremental_max_posts=int(os.getenv("INSTAGRAM_INCREMENTAL_MAX_POSTS", "30")),
        instagram_unchanged_stop_count=int(os.getenv("INSTAGRAM_UNCHANGED_STOP_COUNT", "12")),
    )
