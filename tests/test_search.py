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
