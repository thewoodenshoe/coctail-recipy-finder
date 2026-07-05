from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.db import init_database
from app.ingredient_lists import create_ingredient_list, update_ingredient_list
from app.models import Base, Creator
from app.services import import_caption_to_gold


@pytest.fixture()
def web_db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    init_database(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        yield session


def _client(db_session):
    def override_db():
        yield db_session

    main.app.dependency_overrides[main.get_db] = override_db
    return TestClient(main.app)


def _clear_overrides():
    main.app.dependency_overrides.clear()


def _seed_recipe(db_session, title: str, caption: str, url_slug: str, creator: str = "thirstywhale_"):
    recipe = import_caption_to_gold(
        db_session,
        creator,
        f"https://www.instagram.com/p/{url_slug}/",
        f"{title}\n{caption}",
    )
    db_session.commit()
    return recipe


def test_cocktail_of_the_day_is_stable_for_calendar_day(db_session):
    _seed_recipe(db_session, "Gin Sour", "2 oz gin\n1 oz lemon juice\nShake hard.", "gin-sour")
    _seed_recipe(db_session, "Rum Punch", "2 oz rum\n1 oz lime juice\nShake hard.", "rum-punch")

    first = main.cocktail_of_the_day(db_session, date(2026, 7, 5))
    second = main.cocktail_of_the_day(db_session, date(2026, 7, 5))

    assert first is not None
    assert second is not None
    assert first["id"] == second["id"]


def test_surprise_recipe_uses_offset_without_contiguous_id_assumption(db_session):
    first = _seed_recipe(db_session, "Gin Sour", "2 oz gin\n1 oz lemon juice\nShake hard.", "gin-sour")
    second = _seed_recipe(db_session, "Rum Punch", "2 oz rum\n1 oz lime juice\nShake hard.", "rum-punch")
    db_session.delete(first)
    db_session.commit()

    result = main.random_recipe(db_session, offset=0)

    assert result is not None
    assert result["id"] == second.id
    assert result["detail_path"] == f"/gold/{second.id}"


def test_search_query_submission_renders_results_state(web_db_session):
    _seed_recipe(web_db_session, "Apple Vodka Smash", "2 oz vodka\n1 oz apple cider\n.75 oz lime juice\nShake hard.", "apple-vodka")
    client = _client(web_db_session)
    try:
        response = client.get("/search?q=apple+vodka")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "Recipes that fit." in response.text
    assert "Apple Vodka Smash" in response.text
    assert 'value="apple vodka"' in response.text


def test_filter_chip_selection_deselection_and_clear_all(web_db_session):
    _seed_recipe(web_db_session, "Gin Sour", "2 oz gin\n1 oz lemon juice\nShake hard.", "gin-sour")
    client = _client(web_db_session)
    try:
        response = client.get("/search?alcohol=gin&ingredient=lemon+juice")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "Active filters" in response.text
    assert "Gin" in response.text
    assert "Lemon" in response.text
    assert "Clear all" in response.text


def test_saved_list_matching_flow_marks_cocktails_can_make(web_db_session):
    _seed_recipe(web_db_session, "Apple Vodka Smash", "2 oz vodka\n1 oz apple cider\n.75 oz lime juice\nFresh mint\nShake hard.", "apple-vodka")
    ingredient_list = create_ingredient_list(web_db_session, "Stewart's Ingredients")
    update_ingredient_list(web_db_session, ingredient_list.id, ingredient_list.name, ["vodka"], ["apple", "lime juice", "mint"])
    web_db_session.commit()
    client = _client(web_db_session)
    try:
        response = client.get(f"/?list_id={ingredient_list.id}")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "Stewart&#39;s Ingredients" in response.text
    assert "Apple Vodka Smash" in response.text
    assert "Can make" in response.text


def test_detail_page_renders_recipe_source_and_creator_social_links(web_db_session):
    recipe = _seed_recipe(web_db_session, "Gin Sour", "2 oz gin\n1 oz lemon juice\nShake hard.", "gin-sour")
    creator = web_db_session.query(Creator).filter_by(handle="thirstywhale_").one()
    client = _client(web_db_session)
    try:
        response = client.get(f"/gold/{recipe.id}")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    assert "Original recipe" in response.text
    assert recipe.source_url in response.text
    assert "Creator profile" in response.text
    assert creator.profile_url in response.text


def test_surprise_route_redirects_to_recipe_detail(web_db_session):
    recipe = _seed_recipe(web_db_session, "Gin Sour", "2 oz gin\n1 oz lemon juice\nShake hard.", "gin-sour")
    client = _client(web_db_session)
    try:
        response = client.get("/surprise", follow_redirects=False)
    finally:
        _clear_overrides()

    assert response.status_code == 303
    assert response.headers["location"] == f"/gold/{recipe.id}"
