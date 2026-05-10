from __future__ import annotations

from app.ingestion.base import IngestionResult
from app.models import Creator


class InstagramPublicProvider:
    """Placeholder for a future approved source-text provider.

    Public Instagram collection is intentionally not implemented here. The MVP
    depends on manual or creator-provided source text.
    """

    def backfill(self, creator: Creator) -> IngestionResult:
        return IngestionResult(
            posts=[],
            message=(
                f"Public Instagram backfill for @{creator.handle} is not implemented. "
                "Use manual caption import or a future approved source-text provider."
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
