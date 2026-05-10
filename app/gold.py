from __future__ import annotations

import json
import re
import hashlib
from datetime import datetime, timezone
from typing import Any

from app.ingestion.base import IngestedPost
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.extraction import extract_recipe
from app.models import Creator, GoldRecipe, RawPost, RecipeExtraction


DETERMINISTIC_TRANSFORMER_NAME = "deterministic_recipe_extractor"
DETERMINISTIC_TRANSFORMER_VERSION = "deterministic_recipe_v1"


def normalize_title(title: str | None) -> str | None:
    if not title:
        return None
    tokens = re.findall(r"[A-Za-z0-9]+", title.lower())
    return " ".join(tokens) or None


def rebuild_gold_search_index(session: Session) -> int:
    session.execute(text("DELETE FROM gold_recipe_search_index"))
    rows = session.execute(select(GoldRecipe, RawPost).join(RawPost, GoldRecipe.raw_post_id == RawPost.id)).all()
    for gold_recipe, raw_post in rows:
        update_gold_recipe_search_index(session, gold_recipe, raw_post)
    return len(rows)


def clear_all_data(session: Session) -> None:
    session.execute(text("DELETE FROM gold_recipe_search_index"))
    session.execute(text("DELETE FROM gold_recipes"))
    session.execute(text("DELETE FROM recipe_extractions"))
    session.execute(text("DELETE FROM raw_posts"))
    session.execute(
        text(
            """
            UPDATE creators
            SET last_sync_at = NULL,
                backfill_completed_at = NULL,
                sync_status = 'never_synced',
                sync_error = NULL
            """
        )
    )


def upsert_raw_post_from_ingested(
    session: Session,
    creator: Creator,
    ingested: IngestedPost,
    provider_name: str,
) -> tuple[RawPost, bool]:
    raw_text = (ingested.raw_text or ingested.caption_text).strip()
    caption_text = ingested.caption_text.strip()
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    raw_post = session.scalar(select(RawPost).where(RawPost.source_url == ingested.source_url))
    created = raw_post is None
    now = datetime.now(timezone.utc)
    raw_payload = {
        "raw_text": raw_text,
        "fetch_seconds": ingested.fetch_seconds,
    }
    if raw_post is None:
        raw_post = RawPost(
            platform="instagram",
            creator_id=creator.id,
            creator_handle_snapshot=creator.handle,
            source_url=ingested.source_url,
            external_post_id=ingested.external_post_id,
            captured_at=now,
            content_hash=digest,
            raw_json=json.dumps(raw_payload, ensure_ascii=True),
            raw_caption_text=caption_text,
            raw_hashtags_json=json.dumps(_hashtags(caption_text), ensure_ascii=True),
            raw_thumbnail_url=ingested.raw_thumbnail_url,
            local_image_path=ingested.local_image_path,
            image_capture_status=ingested.image_capture_status,
            image_capture_error=ingested.image_capture_error,
            posted_at=ingested.posted_at,
            capture_completeness="text_only",
            ingestion_provider=provider_name,
            ingestion_status="raw_captured",
        )
        session.add(raw_post)
        session.flush()
    else:
        raw_post.creator_id = creator.id
        raw_post.creator_handle_snapshot = creator.handle
        raw_post.external_post_id = ingested.external_post_id or raw_post.external_post_id
        raw_post.captured_at = now
        raw_post.content_hash = digest
        raw_post.raw_json = json.dumps(raw_payload, ensure_ascii=True)
        raw_post.raw_caption_text = caption_text
        raw_post.raw_hashtags_json = json.dumps(_hashtags(caption_text), ensure_ascii=True)
        raw_post.raw_thumbnail_url = ingested.raw_thumbnail_url or raw_post.raw_thumbnail_url
        raw_post.local_image_path = ingested.local_image_path or raw_post.local_image_path
        raw_post.image_capture_status = ingested.image_capture_status or raw_post.image_capture_status
        raw_post.image_capture_error = ingested.image_capture_error
        raw_post.posted_at = ingested.posted_at or raw_post.posted_at
        raw_post.capture_completeness = "text_only"
        raw_post.ingestion_provider = provider_name
        raw_post.ingestion_status = "raw_captured"
        raw_post.ingestion_error = None
    return raw_post, created


def transform_raw_posts(session: Session, creator_handle: str | None = None) -> dict[str, int]:
    query = select(RawPost, Creator).join(Creator, RawPost.creator_id == Creator.id)
    if creator_handle:
        query = query.where(Creator.handle == creator_handle)
    rows = session.execute(query.order_by(RawPost.id)).all()
    counts = {"processed": 0, "active": 0, "not_recipe": 0, "low_confidence": 0, "failed": 0}
    for raw_post, creator in rows:
        counts["processed"] += 1
        try:
            extraction = create_extraction_from_raw(session, raw_post)
            gold_recipe, _created = upsert_gold_recipe_from_extraction(session, raw_post, extraction, creator)
            update_gold_recipe_search_index(session, gold_recipe, raw_post)
            if gold_recipe.status in counts:
                counts[gold_recipe.status] += 1
        except Exception as exc:
            counts["failed"] += 1
            extraction = RecipeExtraction(
                raw_post_id=raw_post.id,
                transformer_name=DETERMINISTIC_TRANSFORMER_NAME,
                transformer_version=DETERMINISTIC_TRANSFORMER_VERSION,
                status="failed",
                extracted_json="{}",
                confidence_reasons_json="[]",
                error=str(exc),
            )
            session.add(extraction)
    return counts


def create_extraction_from_raw(session: Session, raw_post: RawPost) -> RecipeExtraction:
    parsed = extract_recipe(raw_post.raw_caption_text)
    ingredients = _structured_ingredients(parsed.ingredients)
    status = "success"
    if not ingredients:
        status = "not_recipe"
    elif parsed.confidence_score < 0.5:
        status = "low_confidence"
    extracted = {
        "drink_title": parsed.drink_name,
        "intro_text": parsed.extra_instagram_text,
        "base_spirits": parsed.base_spirits,
        "ingredients": ingredients,
        "method": parsed.method,
        "garnish": parsed.garnish,
        "glassware": None,
        "tags": parsed.tags,
    }
    extraction = session.scalar(
        select(RecipeExtraction).where(
            RecipeExtraction.raw_post_id == raw_post.id,
            RecipeExtraction.transformer_version == DETERMINISTIC_TRANSFORMER_VERSION,
        )
    )
    if extraction is None:
        extraction = RecipeExtraction(
            raw_post_id=raw_post.id,
            transformer_name=DETERMINISTIC_TRANSFORMER_NAME,
            transformer_version=DETERMINISTIC_TRANSFORMER_VERSION,
            status=status,
            extracted_json=json.dumps(extracted, ensure_ascii=True),
            confidence_score=parsed.confidence_score,
            quality_score=_quality_score_from_extracted(extracted, parsed.confidence_score),
            confidence_reasons_json=json.dumps([], ensure_ascii=True),
        )
        session.add(extraction)
        session.flush()
    else:
        extraction.status = status
        extraction.extracted_json = json.dumps(extracted, ensure_ascii=True)
        extraction.confidence_score = parsed.confidence_score
        extraction.quality_score = _quality_score_from_extracted(extracted, parsed.confidence_score)
        extraction.error = None
    return extraction


def upsert_gold_recipe_from_extraction(
    session: Session,
    raw_post: RawPost,
    extraction: RecipeExtraction,
    creator: Creator,
) -> tuple[GoldRecipe, bool]:
    extracted = json.loads(extraction.extracted_json or "{}")
    gold_recipe = session.scalar(select(GoldRecipe).where(GoldRecipe.raw_post_id == raw_post.id))
    created = gold_recipe is None
    status = _gold_status(extraction, extracted)
    if gold_recipe is None:
        gold_recipe = GoldRecipe(
            raw_post_id=raw_post.id,
            creator_id=creator.id,
            creator_handle=creator.handle,
            source_url=raw_post.source_url,
            transformer_version=extraction.transformer_version,
        )
        session.add(gold_recipe)
        session.flush()

    gold_recipe.extraction_id = extraction.id
    gold_recipe.creator_id = creator.id
    gold_recipe.creator_handle = creator.handle
    gold_recipe.source_url = raw_post.source_url
    gold_recipe.drink_title = extracted.get("drink_title")
    gold_recipe.drink_title_normalized = normalize_title(extracted.get("drink_title"))
    gold_recipe.intro_text = extracted.get("intro_text")
    gold_recipe.base_spirits_json = json.dumps(extracted.get("base_spirits") or [], ensure_ascii=True)
    gold_recipe.ingredients_json = json.dumps(extracted.get("ingredients") or [], ensure_ascii=True)
    gold_recipe.method = extracted.get("method")
    gold_recipe.garnish = extracted.get("garnish")
    gold_recipe.glassware = extracted.get("glassware")
    gold_recipe.tags_json = json.dumps(extracted.get("tags") or [], ensure_ascii=True)
    gold_recipe.confidence_score = extraction.confidence_score
    gold_recipe.quality_score = extraction.quality_score
    gold_recipe.view_count = raw_post.raw_view_count
    gold_recipe.like_count = raw_post.raw_like_count
    gold_recipe.posted_at = raw_post.posted_at
    gold_recipe.transformed_at = datetime.now(timezone.utc)
    gold_recipe.transformer_version = extraction.transformer_version
    gold_recipe.status = status
    session.flush()
    return gold_recipe, created


def update_gold_recipe_search_index(
    session: Session,
    gold_recipe: GoldRecipe,
    raw_post: RawPost,
) -> None:
    session.execute(
        text("DELETE FROM gold_recipe_search_index WHERE gold_recipe_id = :id"),
        {"id": gold_recipe.id},
    )
    session.execute(
        text(
            """
            INSERT INTO gold_recipe_search_index (
                gold_recipe_id, source_url, creator_handle, drink_title,
                drink_title_normalized, base_spirits, ingredient_names, tags,
                intro_text, raw_fallback_text
            )
            VALUES (
                :gold_recipe_id, :source_url, :creator_handle, :drink_title,
                :drink_title_normalized, :base_spirits, :ingredient_names, :tags,
                :intro_text, :raw_fallback_text
            )
            """
        ),
        {
            "gold_recipe_id": gold_recipe.id,
            "source_url": gold_recipe.source_url,
            "creator_handle": gold_recipe.creator_handle,
            "drink_title": gold_recipe.drink_title or "",
            "drink_title_normalized": gold_recipe.drink_title_normalized or "",
            "base_spirits": " ".join(_json_list(gold_recipe.base_spirits_json)),
            "ingredient_names": " ".join(_ingredient_terms(gold_recipe.ingredients_json)),
            "tags": " ".join(_json_list(gold_recipe.tags_json)),
            "intro_text": gold_recipe.intro_text or "",
            "raw_fallback_text": raw_post.raw_caption_text or "",
        },
    )


def search_gold_recipes(
    session: Session,
    query: str = "",
    creator_handle: str | None = None,
    base_spirit: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    fts_query = _fts_query(query)
    params: dict[str, Any] = {"limit": limit}
    filters = ["gold_recipes.status = 'active'"]
    if creator_handle:
        filters.append("gold_recipes.creator_handle = :creator_handle")
        params["creator_handle"] = creator_handle
    if base_spirit:
        filters.append("gold_recipes.base_spirits_json LIKE :base_spirit")
        params["base_spirit"] = f'%"{base_spirit.lower()}"%'
    if fts_query:
        params["fts_query"] = fts_query
        filters.append("gold_recipe_search_index MATCH :fts_query")
        rank = "bm25(gold_recipe_search_index, 5.0, 1.0, 3.0, 4.0, 2.0, 1.2, 0.5, 0.1) AS rank"
    else:
        rank = "0 AS rank"
    where = " AND ".join(filters)
    rows = session.execute(
        text(
            f"""
            SELECT gold_recipes.*, raw_posts.local_image_path, {rank}
            FROM gold_recipes
            JOIN raw_posts
                ON raw_posts.id = gold_recipes.raw_post_id
            JOIN gold_recipe_search_index
                ON gold_recipe_search_index.gold_recipe_id = gold_recipes.id
            WHERE {where}
            ORDER BY rank, COALESCE(gold_recipes.quality_score, 0) DESC, gold_recipes.transformed_at DESC
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


def featured_gold_recipes(
    session: Session,
    base_spirit: str | None = None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": limit}
    filters = ["gold_recipes.status = 'active'"]
    if base_spirit:
        filters.append("gold_recipes.base_spirits_json LIKE :base_spirit")
        params["base_spirit"] = f'%"{base_spirit.lower()}"%'
    where = " AND ".join(filters)
    rows = session.execute(
        text(
            f"""
            SELECT
                gold_recipes.*,
                raw_posts.local_image_path,
                COALESCE(gold_recipes.view_count, gold_recipes.like_count, 0) AS popularity_count
            FROM gold_recipes
            JOIN raw_posts
                ON raw_posts.id = gold_recipes.raw_post_id
            WHERE {where}
            ORDER BY
                COALESCE(gold_recipes.view_count, gold_recipes.like_count, 0) DESC,
                COALESCE(gold_recipes.quality_score, 0) DESC,
                gold_recipes.id DESC
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


def _gold_status(extraction: RecipeExtraction, extracted: dict[str, Any]) -> str:
    if extraction.status == "not_recipe" or not extracted.get("ingredients"):
        return "not_recipe"
    if extraction.status == "low_confidence":
        return "low_confidence"
    return "active"


def _quality_score_from_extracted(extracted: dict[str, Any], confidence_score: float | None) -> float:
    score = 0.0
    score += 0.25 if extracted.get("drink_title") else 0
    score += 0.25 if extracted.get("ingredients") else 0
    score += 0.2 if extracted.get("method") else 0
    score += 0.15 if extracted.get("base_spirits") else 0
    score += 0.05 if extracted.get("garnish") else 0
    score += min(confidence_score or 0, 1.0) * 0.1
    return round(min(score, 1.0), 3)


def _structured_ingredients(ingredients: list[str]) -> list[dict[str, str | None]]:
    return [
        {
            "raw_text": ingredient,
            "name": _ingredient_name(ingredient),
            "normalized_name": normalize_title(_ingredient_name(ingredient)),
            "amount": None,
            "unit": None,
        }
        for ingredient in ingredients
    ]


def _ingredient_name(raw_text: str) -> str:
    text_value = re.sub(r"^[\d./-]+\s*(ounces|ounce|cups|cup|grams|g|oz|ml|tbsp|tsp|dashes|dash|parts|part)?\s*(\|\s*[\d./-]+\s*(oz|ml))?\s*", "", raw_text, flags=re.IGNORECASE)
    return text_value.strip() or raw_text


def _ingredient_terms(ingredients_json: str) -> list[str]:
    terms: list[str] = []
    for ingredient in _json_value(ingredients_json, []):
        if isinstance(ingredient, dict):
            terms.extend(
                [
                    str(ingredient.get("normalized_name") or ""),
                    str(ingredient.get("name") or ""),
                    str(ingredient.get("raw_text") or ""),
                ]
            )
        else:
            terms.append(str(ingredient))
    return terms


def _json_list(value: str | None) -> list[str]:
    parsed = _json_value(value, [])
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def _json_value(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _hashtags(text_value: str) -> list[str]:
    return [tag.lower() for tag in re.findall(r"#([A-Za-z0-9_]+)", text_value or "")]


def _fts_query(query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())
    return " ".join(tokens)
