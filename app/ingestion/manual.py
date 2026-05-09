from __future__ import annotations

from app.ingestion.base import IngestedPost


def build_manual_post(source_url: str, caption_text: str) -> IngestedPost:
    return IngestedPost(source_url=source_url.strip(), caption_text=caption_text.strip())
