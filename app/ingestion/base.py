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
    posted_at: datetime | None = None


@dataclass(frozen=True)
class IngestionResult:
    posts: list[IngestedPost]
    message: str = ""


class IngestionProvider(Protocol):
    def backfill(self, creator: Creator) -> IngestionResult:
        ...

    def incremental(self, creator: Creator) -> IngestionResult:
        ...
