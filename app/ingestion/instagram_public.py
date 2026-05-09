from __future__ import annotations

from app.ingestion.base import IngestionResult
from app.models import Creator


class InstagramPublicProvider:
    """Best-effort placeholder for future authorized or browser-assisted import.

    Direct Instagram scraping is intentionally not implemented here. The MVP must not
    depend on brittle scraping, login bypasses, CAPTCHA bypasses, or video downloads.
    """

    def backfill(self, creator: Creator) -> IngestionResult:
        return IngestionResult(
            posts=[],
            message=(
                f"Public Instagram backfill for @{creator.handle} is not implemented. "
                "Use manual caption import or a future authorized/browser-assisted importer."
            ),
        )

    def incremental(self, creator: Creator) -> IngestionResult:
        return IngestionResult(
            posts=[],
            message=(
                f"Public Instagram incremental sync for @{creator.handle} is not implemented. "
                "No posts were fetched."
            ),
        )
