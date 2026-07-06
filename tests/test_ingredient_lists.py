from app.ingredient_lists import (
    create_ingredient_list,
    ingredient_catalog,
    ingredient_list_items,
    update_ingredient_list,
)
from app.main import _optional_int, ranked_recipes_for_ingredient_list, ranked_search_results
from app.services import import_caption_to_gold


def test_ingredient_catalog_uses_recipe_data(db_session):
    import_caption_to_gold(
        db_session,
        "thirstywhale_",
        "https://www.instagram.com/p/apple-vodka/",
        "Apple Vodka Smash\n2 oz vodka\n1 oz apple cider\n.75 oz lime juice\nFresh mint\nShake hard.",
    )
    db_session.commit()

    catalog = ingredient_catalog(db_session)

    assert any(item.name == "vodka" for item in catalog["alcohol"])
    assert any(item.name == "apple" for item in catalog["ingredient"])
    assert any(item.name == "lime juice" for item in catalog["ingredient"])


def test_ingredient_catalog_includes_seeded_more_liquor_options(db_session):
    catalog = ingredient_catalog(db_session)
    alcohol_names = {item.name for item in catalog["alcohol"]}

    assert "st germain" in alcohol_names
    assert "creme de banane" in alcohol_names
    assert "maraschino liqueur" in alcohol_names
    assert "coffee liqueur" in alcohol_names


def test_saved_ingredient_list_persists_items(db_session):
    ingredient_list = create_ingredient_list(db_session, "Stewart's Ingredients")
    update_ingredient_list(db_session, ingredient_list.id, "Stewart's Ingredients", ["vodka"], ["apple", "lime juice"])
    db_session.commit()

    items = ingredient_list_items(db_session, ingredient_list.id)

    assert items["alcohol"] == {"vodka"}
    assert items["ingredient"] == {"apple", "lime juice"}


def test_ingredient_list_ranking_marks_missing_items(db_session):
    import_caption_to_gold(
        db_session,
        "thirstywhale_",
        "https://www.instagram.com/p/apple-vodka/",
        "Apple Vodka Smash\n2 oz vodka\n1 oz apple cider\n.75 oz lime juice\nFresh mint\nShake hard.",
    )
    ingredient_list = create_ingredient_list(db_session, "Stewart's Ingredients")
    update_ingredient_list(db_session, ingredient_list.id, "Stewart's Ingredients", ["vodka"], ["apple", "lime juice", "mint"])
    db_session.commit()

    matches = ranked_recipes_for_ingredient_list(db_session, ingredient_list.id)

    assert matches[0]["drink_name"] == "Apple Vodka Smash"
    assert matches[0]["availability_status"] == "Can make"


def test_specific_liqueur_in_saved_list_matches_recipe(db_session):
    import_caption_to_gold(
        db_session,
        "thirstywhale_",
        "https://www.instagram.com/p/st-germain/",
        "Elderflower Highball\n2 oz gin\n.5 oz St Germain\n.75 oz lemon juice\nShake hard.",
    )
    ingredient_list = create_ingredient_list(db_session, "Liqueur Shelf")
    update_ingredient_list(db_session, ingredient_list.id, "Liqueur Shelf", ["gin", "st germain"], ["lemon juice"])
    db_session.commit()

    matches = ranked_recipes_for_ingredient_list(db_session, ingredient_list.id)

    assert matches[0]["drink_name"] == "Elderflower Highball"
    assert matches[0]["availability_status"] == "Can make"


def test_banana_liqueur_in_saved_list_matches_recipe(db_session):
    import_caption_to_gold(
        db_session,
        "highproofpreacher",
        "https://www.instagram.com/p/banana/",
        "Banana Split\n1 oz rum\n.5 oz Banana Liqueur\n.5 oz lime juice\nShake hard.",
    )
    ingredient_list = create_ingredient_list(db_session, "Tiki Shelf")
    update_ingredient_list(db_session, ingredient_list.id, "Tiki Shelf", ["rum", "creme de banane"], ["lime juice"])
    db_session.commit()

    matches = ranked_recipes_for_ingredient_list(db_session, ingredient_list.id)

    assert matches[0]["drink_name"] == "Banana Split"
    assert matches[0]["availability_status"] == "Can make"


def test_combined_search_prefers_matching_terms(db_session):
    import_caption_to_gold(
        db_session,
        "thirstywhale_",
        "https://www.instagram.com/p/apple-vodka/",
        "Apple Vodka Smash\n2 oz vodka\n1 oz apple cider\n.75 oz lime juice\nShake hard.",
    )
    import_caption_to_gold(
        db_session,
        "thirstywhale_",
        "https://www.instagram.com/p/plain-vodka/",
        "Vodka Sour\n2 oz vodka\n.75 oz lemon juice\nShake hard.",
    )
    db_session.commit()

    results = ranked_search_results(db_session, "apple vodka", [], [])

    assert results[0]["drink_name"] == "Apple Vodka Smash"


def test_empty_list_id_is_ignored_instead_of_validation_error():
    assert _optional_int("") is None
    assert _optional_int(None) is None
    assert _optional_int("not-an-id") is None
    assert _optional_int("42") == 42
