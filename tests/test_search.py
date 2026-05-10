from __future__ import annotations

from app.services import import_post
from app.search import search_posts


def test_search_index_returns_imported_caption(db_session):
    post = import_post(
        db_session,
        "notjustabartender",
        "https://www.instagram.com/p/test/",
        "Gin Sour\n2 oz gin\n1 oz lemon\nShake hard.",
    )
    db_session.commit()

    results = search_posts(db_session, "gin")
    assert results
    assert results[0]["id"] == post.id
    assert results[0]["creator_handle"] == "notjustabartender"
    assert results[0]["base_spirits_json"] == '["gin"]'


def test_search_excludes_non_recipe_posts_without_ingredients(db_session):
    import_post(
        db_session,
        "notjustabartender",
        "https://www.instagram.com/p/no-recipe/",
        "This competition was next level. #ad | @flordecanarum",
    )
    db_session.commit()

    assert search_posts(db_session, "competition") == []
