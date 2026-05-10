from __future__ import annotations

from sqlalchemy import func, select, text

from app.gold import (
    clear_all_data,
    featured_gold_recipes,
    rebuild_gold_search_index,
    search_gold_recipes,
    transform_raw_posts,
    upsert_raw_post_from_ingested,
)
from app.ingestion.base import IngestedPost
from app.models import Creator, GoldRecipe, RawPost, RecipeExtraction


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


def test_rebuild_gold_search_and_query_structured_recipe(db_session):
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
            source_url="https://www.instagram.com/reel/kentucky-buck/",
            caption_text="KENTUCKY BUCK\n3-4 strawberries\n2oz | 60ml Four Roses OESO Single Barrel\nGinger Beer\nShake hard.",
            raw_text="KENTUCKY BUCK\n3-4 strawberries\n2oz | 60ml Four Roses OESO Single Barrel\nGinger Beer\nShake hard.",
        ),
        provider_name="test",
    )
    db_session.commit()
    transform_raw_posts(db_session)
    count = rebuild_gold_search_index(db_session)
    db_session.commit()

    assert count == 1
    results = search_gold_recipes(db_session, "bourbon strawberries")
    assert len(results) == 1
    assert results[0]["drink_title"] == "Kentucky Buck"


def test_gold_search_filters_by_base_spirit(db_session):
    creator = Creator(
        handle="notjustabartender",
        profile_url="https://www.instagram.com/notjustabartender/",
        active=True,
    )
    db_session.add(creator)
    db_session.flush()
    for url, caption in [
        ("https://www.instagram.com/p/gin/", "Gin Sour\n2 oz gin\n1 oz lemon\nShake hard."),
        ("https://www.instagram.com/p/bourbon/", "Gold Rush\n2 oz bourbon\n.75 oz lemon\nShake hard."),
    ]:
        upsert_raw_post_from_ingested(
            db_session,
            creator,
            IngestedPost(source_url=url, caption_text=caption, raw_text=caption),
            provider_name="test",
        )
    transform_raw_posts(db_session)
    db_session.commit()

    results = search_gold_recipes(db_session, base_spirit="gin")

    assert [row["drink_title"] for row in results] == ["Gin Sour"]


def test_featured_gold_recipes_prefers_popularity_then_quality(db_session):
    creator = Creator(
        handle="notjustabartender",
        profile_url="https://www.instagram.com/notjustabartender/",
        active=True,
    )
    db_session.add(creator)
    db_session.flush()
    for url, caption, views in [
        ("https://www.instagram.com/p/low/", "Low View Gin\n2 oz gin\nShake hard.", 10),
        ("https://www.instagram.com/p/high/", "High View Gin\n2 oz gin\n1 oz lemon\nShake hard.", 250),
    ]:
        raw_post, _created = upsert_raw_post_from_ingested(
            db_session,
            creator,
            IngestedPost(source_url=url, caption_text=caption, raw_text=caption),
            provider_name="test",
        )
        raw_post.raw_view_count = views
    transform_raw_posts(db_session)
    db_session.commit()

    results = featured_gold_recipes(db_session, "gin", limit=2)

    assert [row["drink_title"] for row in results] == ["High View Gin", "Low View Gin"]
    assert results[0]["popularity_count"] == 250


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
