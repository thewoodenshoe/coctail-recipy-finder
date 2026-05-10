from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
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
                creator.backfill_completed_at = now
                creator.sync_status = "backfilled"
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
