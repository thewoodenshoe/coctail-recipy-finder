from __future__ import annotations

from app.gold import search_gold_recipes
from app.services import import_caption_to_gold


def test_gold_search_returns_imported_caption(db_session):
    recipe = import_caption_to_gold(
        db_session,
        "notjustabartender",
        "https://www.instagram.com/p/test/",
        "Gin Sour\n2 oz gin\n1 oz lemon\nShake hard.",
    )
    db_session.commit()

    results = search_gold_recipes(db_session, "gin")
    assert results
    assert results[0]["id"] == recipe.id
    assert results[0]["creator_handle"] == "notjustabartender"
    assert results[0]["base_spirits_json"] == '["gin"]'


def test_gold_search_excludes_non_recipe_posts_without_ingredients(db_session):
    import_caption_to_gold(
        db_session,
        "notjustabartender",
        "https://www.instagram.com/p/no-recipe/",
        "This competition was next level. #ad | @flordecanarum",
    )
    db_session.commit()

    assert search_gold_recipes(db_session, "competition") == []
