from __future__ import annotations

from app.main import _display_title, _format_count
from app.gold import search_gold_recipes
from app.services import import_caption_to_gold, import_instagram_jsonl_to_gold


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


def test_result_display_helpers_hide_bad_title_and_zero_count():
    assert _display_title({"drink_title": "Ingredients:", "creator_handle": "join_jules"}, ["2 oz gin"]) == "2 oz gin cocktail"
    assert _format_count(0) == ""


def test_bulk_jsonl_import_writes_searchable_gold(db_session, tmp_path):
    path = tmp_path / "captured.jsonl"
    path.write_text(
        """
{"creator_handle":"thirstywhale_","canonical_url":"https://www.instagram.com/reel/DY5bg_fRGLt/","post_id":"DY5bg_fRGLt","ok":true,"caption_text":"ESPRESSO TINI\\n1.5 oz vodka\\n1.5 oz espresso\\n0.5 oz coffee liqueur\\nShake hard.","image_url":"https://cdn.example/thumb.jpg"}
{"creator_handle":"thirstywhale_","canonical_url":"https://www.instagram.com/p/no-recipe/","post_id":"no-recipe","ok":true,"caption_text":"Quick cold and rainy camp weekend."}
""".strip()
        + "\n"
    )

    result = import_instagram_jsonl_to_gold(db_session, "thirstywhale_", path)
    db_session.commit()

    assert result.imported == 2
    assert result.active == 1
    assert result.not_recipe == 1
    results = search_gold_recipes(db_session, "espresso", creator_handle="thirstywhale_")
    assert [row["drink_title"] for row in results] == ["Espresso Tini"]


def test_bulk_jsonl_import_can_replace_creator_data(db_session, tmp_path):
    first = tmp_path / "first.jsonl"
    first.write_text(
        '{"creator_handle":"thirstywhale_","canonical_url":"https://www.instagram.com/reel/old/","ok":true,"caption_text":"Old Gin\\n2 oz gin\\nShake hard."}\n'
    )
    second = tmp_path / "second.jsonl"
    second.write_text(
        '{"creator_handle":"thirstywhale_","canonical_url":"https://www.instagram.com/reel/new/","ok":true,"caption_text":"New Rum\\n2 oz rum\\nShake hard."}\n'
    )

    import_instagram_jsonl_to_gold(db_session, "thirstywhale_", first)
    import_instagram_jsonl_to_gold(db_session, "thirstywhale_", second, replace_creator_data=True)
    db_session.commit()

    assert search_gold_recipes(db_session, "old", creator_handle="thirstywhale_") == []
    assert [row["drink_title"] for row in search_gold_recipes(db_session, "new", creator_handle="thirstywhale_")] == ["New Rum"]
