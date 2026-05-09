from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.creators import CreatorConfig, load_creator_config, normalize_handle
from app.extraction import extract_recipe
from app.ingestion.base import IngestedPost, IngestionProvider
from app.ingestion.instagram_public import InstagramPublicProvider
from app.models import Creator, Post, Recipe
from app.search import update_post_search_index


@dataclass(frozen=True)
class SyncAction:
    handle: str
    action: str
    status: str
    message: str = ""


def content_hash(caption_text: str) -> str:
    return hashlib.sha256(caption_text.encode("utf-8")).hexdigest()


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


def import_post(session: Session, creator_handle: str, source_url: str, caption_text: str) -> Post:
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

    ingested = IngestedPost(source_url=source_url, caption_text=caption_text)
    return upsert_post(session, creator, ingested)


def upsert_post(session: Session, creator: Creator, ingested: IngestedPost) -> Post:
    source_url = ingested.source_url.strip()
    caption_text = ingested.caption_text.strip()
    if not source_url:
        raise ValueError("Source URL is required")
    if not caption_text:
        raise ValueError("Caption text is required")

    post = session.scalar(select(Post).where(Post.source_url == source_url))
    digest = content_hash(caption_text)
    if post is None:
        post = Post(
            creator_id=creator.id,
            source_platform="instagram",
            source_url=source_url,
            external_post_id=ingested.external_post_id,
            caption_text=caption_text,
            posted_at=ingested.posted_at,
            content_hash=digest,
        )
        session.add(post)
        session.flush()
    elif post.content_hash != digest:
        post.caption_text = caption_text
        post.external_post_id = ingested.external_post_id or post.external_post_id
        post.posted_at = ingested.posted_at or post.posted_at
        post.content_hash = digest
        post.updated_at = datetime.now(timezone.utc)
        session.flush()

    recipe_data = extract_recipe(caption_text)
    if post.recipe is None:
        post.recipe = Recipe(post_id=post.id, ingredients_json="[]")

    post.recipe.drink_name = recipe_data.drink_name
    post.recipe.base_spirit = recipe_data.base_spirit
    post.recipe.ingredients_json = recipe_data.ingredients_json()
    post.recipe.method = recipe_data.method
    post.recipe.garnish = recipe_data.garnish
    post.recipe.confidence_score = recipe_data.confidence_score
    session.flush()
    session.refresh(post)
    update_post_search_index(session, post)
    return post


def sync_creators_from_config(
    session: Session,
    config_path,
    provider: IngestionProvider | None = None,
) -> list[SyncAction]:
    provider = provider or InstagramPublicProvider()
    configs = load_creator_config(config_path)
    actions: list[SyncAction] = []
    now = datetime.now(timezone.utc)

    for config in configs:
        creator, _is_new = upsert_creator(session, config)
        session.flush()
        decision = sync_decision(creator)
        if decision == "skip":
            creator.sync_status = "skipped_inactive"
            actions.append(SyncAction(creator.handle, "skip", "skipped"))
            continue

        try:
            result = provider.backfill(creator) if decision == "backfill" else provider.incremental(creator)
            for ingested in result.posts:
                upsert_post(session, creator, ingested)
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
                    result.message or f"{len(result.posts)} posts imported",
                )
            )
        except Exception as exc:
            creator.last_sync_at = now
            creator.sync_status = "failed"
            creator.sync_error = str(exc)
            actions.append(SyncAction(creator.handle, decision, "failed", str(exc)))

    return actions
