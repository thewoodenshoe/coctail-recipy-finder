from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.extraction import extract_recipe
from app.models import Creator, GoldRecipe, Post, RawPost, Recipe, RecipeExtraction


LEGACY_TRANSFORMER_NAME = "legacy_migration"
LEGACY_TRANSFORMER_VERSION = "legacy_migration_v1"


def normalize_title(title: str | None) -> str | None:
    if not title:
        return None
    tokens = re.findall(r"[A-Za-z0-9]+", title.lower())
    return " ".join(tokens) or None


def migrate_legacy_to_gold(session: Session) -> dict[str, int]:
    counts = {"raw_posts": 0, "recipe_extractions": 0, "gold_recipes": 0}
    posts = session.scalars(select(Post).order_by(Post.id)).all()
    for post in posts:
        raw_post, raw_created = upsert_raw_post_from_legacy(session, post)
        extraction, extraction_created = upsert_extraction_from_legacy(session, raw_post, post.recipe)
        gold_recipe, gold_created = upsert_gold_recipe_from_extraction(
            session,
            raw_post,
            extraction,
            post.creator,
        )
        update_gold_recipe_search_index(session, gold_recipe, raw_post)
        counts["raw_posts"] += int(raw_created)
        counts["recipe_extractions"] += int(extraction_created)
        counts["gold_recipes"] += int(gold_created)
    return counts


def rebuild_gold_search_index(session: Session) -> int:
    session.execute(text("DELETE FROM gold_recipe_search_index"))
    rows = session.execute(select(GoldRecipe, RawPost).join(RawPost, GoldRecipe.raw_post_id == RawPost.id)).all()
    for gold_recipe, raw_post in rows:
        update_gold_recipe_search_index(session, gold_recipe, raw_post)
    return len(rows)


def upsert_raw_post_from_legacy(session: Session, post: Post) -> tuple[RawPost, bool]:
    raw_post = session.scalar(select(RawPost).where(RawPost.source_url == post.source_url))
    created = raw_post is None
    if raw_post is None:
        raw_post = RawPost(
            platform=post.source_platform,
            creator_id=post.creator_id,
            creator_handle_snapshot=post.creator.handle,
            source_url=post.source_url,
            external_post_id=post.external_post_id,
            captured_at=post.raw_fetched_at or post.discovered_at,
            content_hash=post.content_hash,
            raw_caption_text=post.caption_text,
            raw_json=json.dumps(
                {
                    "legacy_post_id": post.id,
                    "raw_text": post.raw_text,
                },
                ensure_ascii=True,
            ),
            raw_hashtags_json=json.dumps(_hashtags(post.caption_text), ensure_ascii=True),
            posted_at=post.posted_at,
            capture_completeness="legacy_text_only",
            ingestion_provider="legacy_migration",
            ingestion_status="raw_captured",
        )
        session.add(raw_post)
        session.flush()
    else:
        raw_post.creator_id = post.creator_id
        raw_post.creator_handle_snapshot = post.creator.handle
        raw_post.external_post_id = post.external_post_id or raw_post.external_post_id
        raw_post.content_hash = post.content_hash
        raw_post.raw_caption_text = post.caption_text
        raw_post.raw_hashtags_json = json.dumps(_hashtags(post.caption_text), ensure_ascii=True)
    return raw_post, created


def upsert_extraction_from_legacy(
    session: Session,
    raw_post: RawPost,
    recipe: Recipe | None,
) -> tuple[RecipeExtraction, bool]:
    extraction = session.scalar(
        select(RecipeExtraction).where(
            RecipeExtraction.raw_post_id == raw_post.id,
            RecipeExtraction.transformer_version == LEGACY_TRANSFORMER_VERSION,
        )
    )
    created = extraction is None
    status = _legacy_status(recipe)
    extracted = _legacy_extracted_json(raw_post, recipe)
    if extraction is None:
        extraction = RecipeExtraction(
            raw_post_id=raw_post.id,
            transformer_name=LEGACY_TRANSFORMER_NAME,
            transformer_version=LEGACY_TRANSFORMER_VERSION,
            status=status,
            extracted_json=json.dumps(extracted, ensure_ascii=True),
            confidence_score=recipe.confidence_score if recipe else None,
            quality_score=_quality_score(recipe),
            confidence_reasons_json=json.dumps([], ensure_ascii=True),
        )
        session.add(extraction)
        session.flush()
    else:
        extraction.status = status
        extraction.extracted_json = json.dumps(extracted, ensure_ascii=True)
        extraction.confidence_score = recipe.confidence_score if recipe else None
        extraction.quality_score = _quality_score(recipe)
    return extraction, created


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


def search_gold_recipes(session: Session, query: str = "", limit: int = 50) -> list[dict[str, Any]]:
    fts_query = _fts_query(query)
    params: dict[str, Any] = {"limit": limit}
    if fts_query:
        params["fts_query"] = fts_query
        where = "gold_recipe_search_index MATCH :fts_query AND gold_recipes.status = 'active'"
        rank = "bm25(gold_recipe_search_index, 5.0, 1.0, 3.0, 4.0, 2.0, 1.2, 0.5, 0.1) AS rank"
    else:
        where = "gold_recipes.status = 'active'"
        rank = "0 AS rank"
    rows = session.execute(
        text(
            f"""
            SELECT gold_recipes.*, {rank}
            FROM gold_recipes
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


def _legacy_extracted_json(raw_post: RawPost, recipe: Recipe | None) -> dict[str, Any]:
    if recipe is None:
        parsed = extract_recipe(raw_post.raw_caption_text)
        return {
            "drink_title": parsed.drink_name,
            "intro_text": parsed.extra_instagram_text,
            "base_spirits": parsed.base_spirits,
            "ingredients": _structured_ingredients(parsed.ingredients),
            "method": parsed.method,
            "garnish": parsed.garnish,
            "glassware": None,
            "tags": parsed.tags,
        }
    return {
        "drink_title": recipe.drink_name,
        "intro_text": recipe.extra_instagram_text,
        "base_spirits": _json_list(recipe.base_spirits_json),
        "ingredients": _structured_ingredients(_json_list(recipe.ingredients_json)),
        "method": recipe.method,
        "garnish": recipe.garnish,
        "glassware": None,
        "tags": _json_list(raw_post.raw_hashtags_json),
    }


def _legacy_status(recipe: Recipe | None) -> str:
    if recipe is None:
        return "not_recipe"
    if not _json_list(recipe.ingredients_json):
        return "not_recipe"
    if recipe.confidence_score is not None and recipe.confidence_score < 0.5:
        return "low_confidence"
    return "success"


def _gold_status(extraction: RecipeExtraction, extracted: dict[str, Any]) -> str:
    if extraction.status == "not_recipe" or not extracted.get("ingredients"):
        return "not_recipe"
    if extraction.status == "low_confidence":
        return "low_confidence"
    return "active"


def _quality_score(recipe: Recipe | None) -> float:
    if recipe is None:
        return 0.0
    score = 0.0
    score += 0.25 if recipe.drink_name else 0
    score += 0.25 if _json_list(recipe.ingredients_json) else 0
    score += 0.2 if recipe.method else 0
    score += 0.15 if _json_list(recipe.base_spirits_json) else 0
    score += 0.05 if recipe.garnish else 0
    score += min(recipe.confidence_score or 0, 1.0) * 0.1
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
    text_value = re.sub(r"^[\d./-]+\s*(oz|ml|g|grams|cup|cups|tsp|tbsp|dash|dashes|part|parts)?\s*(\|\s*[\d./-]+\s*(oz|ml))?\s*", "", raw_text, flags=re.IGNORECASE)
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
