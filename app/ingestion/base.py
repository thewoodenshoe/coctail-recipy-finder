from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models import Creator


@dataclass(frozen=True)
class IngestedPost:
    source_url: str
    caption_text: str
    raw_text: str | None = None
    external_post_id: str | None = None
    raw_thumbnail_url: str | None = None
    local_image_path: str | None = None
    image_capture_status: str | None = None
    image_capture_error: str | None = None
    posted_at: datetime | None = None
    fetch_seconds: float | None = None


@dataclass(frozen=True)
class IngestionResult:
    posts: list[IngestedPost]
    message: str = ""


class IngestionProvider(Protocol):
    def backfill(self, creator: Creator) -> IngestionResult:
        ...

    def incremental(self, creator: Creator) -> IngestionResult:
        ...
