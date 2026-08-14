from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.creators import CreatorConfig, load_creator_config, normalize_handle
from app.gold import (
    transform_raw_posts,
    upsert_raw_post_from_ingested,
)
from app.ingestion.base import IngestedPost, IngestionProvider
from app.ingestion.instagram_public import InstagramPublicProvider
from app.models import Creator, GoldRecipe


@dataclass(frozen=True)
class SyncAction:
    handle: str
    action: str
    status: str
    message: str = ""


@dataclass(frozen=True)
class BulkImportResult:
    creator_handle: str
    rows_seen: int
    imported: int
    skipped: int
    active: int
    not_recipe: int
    low_confidence: int
    failed: int


def provider_for_name(name: str | None) -> IngestionProvider:
    provider_name = (name or "public").strip().lower()
    if provider_name in {"public", "instagram-public"}:
        return InstagramPublicProvider()
    raise ValueError(f"Unknown ingestion provider: {name}")


def upsert_creator(session: Session, config: CreatorConfig) -> tuple[Creator, bool]:
    handle = normalize_handle(config.handle)
    creator = session.scalar(select(Creator).where(Creator.handle == handle))
    is_new = creator is None
    if creator is None:
        creator = Creator(
            handle=handle,
            profile_url=config.profile_url,
            display_name=config.display_name,
            active=config.active,
            sync_status="never_synced",
        )
        session.add(creator)
        session.flush()
    else:
        creator.profile_url = config.profile_url
        creator.display_name = config.display_name or creator.display_name
        creator.active = config.active
    return creator, is_new


def sync_decision(creator: Creator) -> str:
    if not creator.active:
        return "skip"
    if creator.backfill_completed_at is None:
        return "backfill"
    return "incremental"


def import_caption_to_gold(
    session: Session,
    creator_handle: str,
    source_url: str,
    caption_text: str,
) -> GoldRecipe:
    handle = normalize_handle(creator_handle)
    creator = session.scalar(select(Creator).where(Creator.handle == handle))
    if creator is None:
        creator = Creator(
            handle=handle,
            profile_url=f"https://www.instagram.com/{handle}/",
            sync_status="manual_only",
            active=True,
        )
        session.add(creator)
        session.flush()

    ingested = IngestedPost(source_url=source_url, caption_text=caption_text, raw_text=caption_text)
    raw_post, _created = upsert_raw_post_from_ingested(
        session,
        creator,
        ingested,
        provider_name="manual_import",
    )
    transform_raw_posts(session, creator.handle)
    gold = session.scalar(select(GoldRecipe).where(GoldRecipe.raw_post_id == raw_post.id))
    if gold is None:
        raise RuntimeError("Manual import did not produce a gold recipe record")
    return gold


def import_instagram_jsonl_to_gold(
    session: Session,
    creator_handle: str,
    jsonl_path: str | Path,
    profile_url: str | None = None,
    transform: bool = True,
    replace_creator_data: bool = False,
) -> BulkImportResult:
    handle = normalize_handle(creator_handle)
    creator_config = CreatorConfig(
        handle=handle,
        profile_url=profile_url or f"https://www.instagram.com/{handle}/",
        active=True,
    )
    creator, _is_new = upsert_creator(session, creator_config)
    if replace_creator_data:
        _clear_creator_pipeline_data(session, creator.handle)
    creator.sync_status = "jsonl_importing"
    session.flush()

    rows_seen = 0
    imported = 0
    skipped = 0
    path = Path(jsonl_path)
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            rows_seen += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}") from exc
            if row.get("creator_handle") and normalize_handle(str(row["creator_handle"])) != handle:
                skipped += 1
                continue
            if row.get("ok") is False:
                skipped += 1
                continue
            source_url = _jsonl_source_url(row)
            if not source_url:
                skipped += 1
                continue
            caption_text = str(row.get("caption_text") or "").strip()
            raw_text = str(row.get("og_description") or caption_text).strip() or caption_text
            ingested = IngestedPost(
                source_url=source_url,
                caption_text=caption_text,
                raw_text=raw_text,
                external_post_id=str(row.get("post_id") or "").strip() or None,
                raw_thumbnail_url=str(row.get("image_url") or "").strip() or None,
                image_capture_status="metadata_only" if row.get("image_url") else "missing_public_image_metadata",
                posted_at=_jsonl_posted_at(row),
                raw_view_count=_jsonl_int(row.get("view_count")),
                raw_like_count=_jsonl_int(row.get("like_count")),
                raw_comment_count=_jsonl_int(row.get("comment_count")),
            )
            upsert_raw_post_from_ingested(
                session,
                creator,
                ingested,
                provider_name="jsonl_caption_import",
            )
            imported += 1

    counts = {"active": 0, "not_recipe": 0, "low_confidence": 0, "failed": 0}
    if transform:
        transform_counts = transform_raw_posts(session, creator.handle)
        counts = {
            "active": transform_counts["active"],
            "not_recipe": transform_counts["not_recipe"],
            "low_confidence": transform_counts["low_confidence"],
            "failed": transform_counts["failed"],
        }
    now = datetime.now(timezone.utc)
    creator.last_sync_at = now
    creator.backfill_completed_at = now
    creator.sync_error = None
    creator.sync_status = "jsonl_imported"
    return BulkImportResult(
        creator_handle=creator.handle,
        rows_seen=rows_seen,
        imported=imported,
        skipped=skipped,
        active=counts["active"],
        not_recipe=counts["not_recipe"],
        low_confidence=counts["low_confidence"],
        failed=counts["failed"],
    )


def _jsonl_source_url(row: dict) -> str:
    for key in ("canonical_url", "final_url", "original_url", "source_url", "url"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return ""


def _jsonl_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return None


def _jsonl_posted_at(row: dict) -> datetime | None:
    raw_value = str(row.get("posted_at") or "").strip()
    if raw_value:
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if parsed is not None:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    posted_at_label = str(row.get("posted_at_label") or "").strip()
    if not posted_at_label:
        return None
    for date_format in ("%B %d, %Y", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(posted_at_label, date_format)
        except ValueError:
            continue
        return parsed.replace(tzinfo=timezone.utc)
    return None


def _clear_creator_pipeline_data(session: Session, creator_handle: str) -> None:
    session.execute(
        text(
            """
            DELETE FROM gold_recipe_search_index
            WHERE gold_recipe_id IN (
                SELECT id FROM gold_recipes WHERE creator_handle = :creator_handle
            )
            """
        ),
        {"creator_handle": creator_handle},
    )
    session.execute(
        text("DELETE FROM gold_recipes WHERE creator_handle = :creator_handle"),
        {"creator_handle": creator_handle},
    )
    session.execute(
        text(
            """
            DELETE FROM recipe_extractions
            WHERE raw_post_id IN (
                SELECT raw_posts.id
                FROM raw_posts
                JOIN creators ON creators.id = raw_posts.creator_id
                WHERE creators.handle = :creator_handle
            )
            """
        ),
        {"creator_handle": creator_handle},
    )
    session.execute(
        text(
            """
            DELETE FROM raw_posts
            WHERE creator_id IN (
                SELECT id FROM creators WHERE handle = :creator_handle
            )
            """
        ),
        {"creator_handle": creator_handle},
    )


def sync_creators_from_config(
    session: Session,
    config_path,
    provider: IngestionProvider | None = None,
    force_backfill: bool = False,
    only_handle: str | None = None,
) -> list[SyncAction]:
    provider = provider or InstagramPublicProvider()
    configs = load_creator_config(config_path)
    if only_handle:
        normalized_only_handle = normalize_handle(only_handle)
        configs = [config for config in configs if normalize_handle(config.handle) == normalized_only_handle]
    actions: list[SyncAction] = []
    now = datetime.now(timezone.utc)

    for config in configs:
        creator, _is_new = upsert_creator(session, config)
        session.flush()
        decision = "backfill" if force_backfill and creator.active else sync_decision(creator)
        if decision == "skip":
            creator.sync_status = "skipped_inactive"
            actions.append(SyncAction(creator.handle, "skip", "skipped"))
            continue

        try:
            result = provider.backfill(creator) if decision == "backfill" else provider.incremental(creator)
            imported = 0
            for ingested in result.posts:
                upsert_raw_post_from_ingested(
                    session,
                    creator,
                    ingested,
                    provider_name=provider.__class__.__name__,
                )
                imported += 1
            transform_counts = transform_raw_posts(session, creator.handle)
            creator.last_sync_at = now
            creator.sync_error = None
            if decision == "backfill":
                if imported:
                    creator.backfill_completed_at = now
                    creator.sync_status = "backfilled"
                else:
                    creator.backfill_completed_at = None
                    creator.sync_status = "backfill_no_posts"
            else:
                creator.sync_status = "incremental_synced"
            actions.append(
                SyncAction(
                    creator.handle,
                    decision,
                    creator.sync_status,
                    result.message
                    or (
                        f"{imported} raw posts imported; "
                        f"{transform_counts['active']} active recipes, "
                        f"{transform_counts['not_recipe']} non-recipes"
                    ),
                )
            )
        except Exception as exc:
            creator.last_sync_at = now
            creator.sync_status = "failed"
            creator.sync_error = str(exc)
            actions.append(SyncAction(creator.handle, decision, "failed", str(exc)))

    return actions
