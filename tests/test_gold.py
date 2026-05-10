from __future__ import annotations

from sqlalchemy import func, select, text

from app.gold import (
    clear_all_data,
    migrate_legacy_to_gold,
    rebuild_gold_search_index,
    search_gold_recipes,
    transform_raw_posts,
    upsert_raw_post_from_ingested,
)
from app.ingestion.base import IngestedPost
from app.models import Creator, GoldRecipe, RawPost, RecipeExtraction
from app.services import import_post


def test_gold_schema_initializes(db_session):
    tables = {
        row[0]
        for row in db_session.execute(
            text("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')")
        ).all()
    }

    assert "raw_posts" in tables
    assert "recipe_extractions" in tables
    assert "gold_recipes" in tables


def test_migrate_legacy_posts_to_raw_extraction_and_gold(db_session):
    post = import_post(
        db_session,
        "notjustabartender",
        "https://www.instagram.com/reel/DXnYlmJjk48/",
        "PINK PONY CLUB\n.25oz | 7.5ml Campari\n1.5oz | 45ml gin\nShake hard.",
    )
    db_session.commit()

    counts = migrate_legacy_to_gold(db_session)
    db_session.commit()

    assert counts == {"raw_posts": 1, "recipe_extractions": 1, "gold_recipes": 1}
    raw_post = db_session.scalar(select(RawPost).where(RawPost.source_url == post.source_url))
    assert raw_post is not None
    extraction = db_session.scalar(select(RecipeExtraction).where(RecipeExtraction.raw_post_id == raw_post.id))
    assert extraction is not None
    assert extraction.transformer_version == "legacy_migration_v1"
    gold = db_session.scalar(select(GoldRecipe).where(GoldRecipe.raw_post_id == raw_post.id))
    assert gold is not None
    assert gold.drink_title == "Pink Pony Club"
    assert gold.status == "active"


def test_migrate_legacy_to_gold_is_idempotent(db_session):
    import_post(
        db_session,
        "notjustabartender",
        "https://www.instagram.com/reel/one/",
        "Gin Sour\n2 oz gin\nShake hard.",
    )
    db_session.commit()

    first = migrate_legacy_to_gold(db_session)
    second = migrate_legacy_to_gold(db_session)
    db_session.commit()

    assert first == {"raw_posts": 1, "recipe_extractions": 1, "gold_recipes": 1}
    assert second == {"raw_posts": 0, "recipe_extractions": 0, "gold_recipes": 0}
    assert db_session.scalar(select(func.count(RawPost.id))) == 1
    assert db_session.scalar(select(func.count(RecipeExtraction.id))) == 1
    assert db_session.scalar(select(func.count(GoldRecipe.id))) == 1


def test_non_recipe_migrates_as_not_recipe_and_is_excluded_from_gold_search(db_session):
    import_post(
        db_session,
        "notjustabartender",
        "https://www.instagram.com/reel/no-recipe/",
        "This competition was next level. #ad | @flordecanarum",
    )
    db_session.commit()

    migrate_legacy_to_gold(db_session)
    db_session.commit()

    gold = db_session.scalar(select(GoldRecipe))
    assert gold is not None
    assert gold.status == "not_recipe"
    assert search_gold_recipes(db_session, "competition") == []


def test_rebuild_gold_search_and_query_structured_recipe(db_session):
    import_post(
        db_session,
        "notjustabartender",
        "https://www.instagram.com/reel/kentucky-buck/",
        "KENTUCKY BUCK\n3-4 strawberries\n2oz | 60ml Four Roses OESO Single Barrel\nGinger Beer\nShake hard.",
    )
    db_session.commit()
    migrate_legacy_to_gold(db_session)
    count = rebuild_gold_search_index(db_session)
    db_session.commit()

    assert count == 1
    results = search_gold_recipes(db_session, "bourbon strawberries")
    assert len(results) == 1
    assert results[0]["drink_title"] == "Kentucky Buck"


def test_transform_raw_posts_creates_extraction_and_gold(db_session):
    creator = Creator(
        handle="notjustabartender",
        profile_url="https://www.instagram.com/notjustabartender/",
        active=True,
    )
    db_session.add(creator)
    db_session.flush()
    upsert_raw_post_from_ingested(
        db_session,
        creator,
        IngestedPost(
            source_url="https://www.instagram.com/reel/raw/",
            caption_text="PINK PONY CLUB\n.25oz | 7.5ml Campari\n1.5oz | 45ml gin\nShake hard.",
            raw_text="notjustabartender\nPINK PONY CLUB\n.25oz | 7.5ml Campari\n1.5oz | 45ml gin\nShake hard.",
            external_post_id="raw",
        ),
        provider_name="test",
    )
    db_session.commit()

    counts = transform_raw_posts(db_session, "notjustabartender")
    db_session.commit()

    assert counts["processed"] == 1
    assert counts["active"] == 1
    assert db_session.scalar(select(func.count(RecipeExtraction.id))) == 1
    gold = db_session.scalar(select(GoldRecipe))
    assert gold is not None
    assert gold.drink_title == "Pink Pony Club"
    assert gold.status == "active"


def test_clear_all_data_keeps_creators_but_removes_pipeline_rows(db_session):
    creator = Creator(
        handle="notjustabartender",
        profile_url="https://www.instagram.com/notjustabartender/",
        active=True,
        sync_status="backfilled",
    )
    db_session.add(creator)
    db_session.flush()
    upsert_raw_post_from_ingested(
        db_session,
        creator,
        IngestedPost(
            source_url="https://www.instagram.com/reel/raw/",
            caption_text="Gin Sour\n2 oz gin\nShake hard.",
            raw_text="Gin Sour\n2 oz gin\nShake hard.",
        ),
        provider_name="test",
    )
    transform_raw_posts(db_session)
    db_session.commit()

    clear_all_data(db_session)
    db_session.commit()

    assert db_session.scalar(select(func.count(Creator.id))) == 1
    assert db_session.scalar(select(func.count(RawPost.id))) == 0
    assert db_session.scalar(select(func.count(RecipeExtraction.id))) == 0
    assert db_session.scalar(select(func.count(GoldRecipe.id))) == 0
    assert db_session.scalar(select(Creator.sync_status)) == "never_synced"
