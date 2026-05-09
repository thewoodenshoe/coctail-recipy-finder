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


def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./cocktail_index.db"),
        creator_config_path=Path(
            os.getenv("CREATOR_CONFIG_PATH", str(BASE_DIR / "config" / "creators.yml"))
        ),
    )
