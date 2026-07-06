from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.config import BASE_DIR, get_settings
from app.db import get_db, init_database
from app.ingredient_lists import (
    create_ingredient_list,
    delete_ingredient_list,
    display_item_name,
    ingredient_catalog,
    ingredient_list_items,
    list_ingredient_lists,
    selected_ingredient_list,
    specific_alcohol_labels,
    update_ingredient_list,
)
from app.models import Creator, GoldRecipe, RawPost


app = FastAPI(title="Cocktail Recipe Finder")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
get_settings().media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.mount("/media", StaticFiles(directory=str(get_settings().media_dir)), name="media")

@app.on_event("startup")
def startup() -> None:
    init_database()


@app.get("/")
def home(
    request: Request,
    q: str = "",
    creator: str = "",
    list_id: str | None = None,
    db: Session = Depends(get_db),
):
    parsed_list_id = _optional_int(list_id)
    list_action = request.query_params.get("list_action")
    if list_action:
        return _handle_ingredient_list_get_action(request, db)
    if request.query_params.get("view") == "top":
        return _popular_response(request, db)
    if request.query_params.get("view") == "my-list":
        return _ingredient_list_response(request, db, parsed_list_id)
    return _search_response(request, db, q, creator, parsed_list_id, page_mode="discover")


@app.get("/search")
def search_page(
    request: Request,
    q: str = "",
    creator: str = "",
    list_id: str | None = None,
    db: Session = Depends(get_db),
):
    return _search_response(request, db, q, creator, _optional_int(list_id), page_mode="search")


@app.get("/surprise")
def surprise_me(db: Session = Depends(get_db)):
    recipe = random_recipe(db)
    if recipe is None:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(recipe["detail_path"], status_code=303)


def _search_response(
    request: Request,
    db: Session,
    q: str,
    creator: str,
    parsed_list_id: int | None,
    page_mode: str,
):
    creators = db.scalars(select(Creator).order_by(Creator.handle)).all()
    catalog = ingredient_catalog(db)
    selected_alcohol = _selected_values(request, "alcohol")
    legacy_base = request.query_params.get("base")
    if legacy_base:
        legacy_base = " ".join(legacy_base.lower().split())
    if legacy_base and legacy_base not in selected_alcohol:
        selected_alcohol.append(legacy_base)
    selected_ingredients = _selected_values(request, "ingredient")
    saved_lists = list_ingredient_lists(db)
    active_search = bool(q or creator or selected_alcohol or selected_ingredients)
    decorated_results = ranked_search_results(
        db,
        q,
        selected_alcohol,
        selected_ingredients,
        creator or None,
        limit=60,
    ) if active_search else []
    current_list = selected_ingredient_list(db, parsed_list_id)
    ingredient_list_matches = ranked_recipes_for_ingredient_list(db, current_list.id, limit=18) if current_list else []
    visible_alcohol, more_alcohol = _split_alcohol_options(catalog["alcohol"])
    visible_ingredients, more_ingredients = _split_ingredient_options(catalog["ingredient"])
    if request.query_params.get("alcohol_sort") == "alpha":
        more_alcohol = sorted(more_alcohol, key=lambda option: option.label)
    if request.query_params.get("ingredient_sort") == "alpha":
        more_ingredients = sorted(more_ingredients, key=lambda option: option.label)
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "q": q,
            "creator_filter": creator,
            "selected_alcohol": selected_alcohol,
            "selected_ingredients": selected_ingredients,
            "selected_filters": _active_filter_chips(request, catalog, selected_alcohol, selected_ingredients),
            "popular_alcohol": _option_cards(request, visible_alcohol, selected_alcohol, "alcohol"),
            "more_alcohol": more_alcohol,
            "alcohol_sort_href": _toggle_sort_url(request, "alcohol_sort"),
            "alcohol_sort_label": "Popular" if request.query_params.get("alcohol_sort") == "alpha" else "A-Z",
            "popular_ingredients": _option_cards(request, visible_ingredients, selected_ingredients, "ingredient"),
            "more_ingredients": more_ingredients,
            "ingredient_sort_href": _toggle_sort_url(request, "ingredient_sort"),
            "ingredient_sort_label": "Popular" if request.query_params.get("ingredient_sort") == "alpha" else "A-Z",
            "all_alcohol_options": catalog["alcohol"],
            "all_ingredient_options": catalog["ingredient"],
            "creators": creators,
            "results": decorated_results if active_search else [],
            "active_search": active_search,
            "ingredient_lists": saved_lists,
            "selected_ingredient_list": current_list,
            "ingredient_list_matches": ingredient_list_matches,
            "ingredient_list_counts": _ingredient_list_counts(db),
            "page_mode": page_mode,
            "cocktail_of_day": cocktail_of_the_day(db),
            "popular_recipes": popular_recipe_results(db, limit=8),
            "popular_classics": popular_classics(db),
            "featured_creators": featured_creators(db, limit=5),
            "search_suggestions": search_suggestions(db),
        },
    )


def _handle_ingredient_list_get_action(request: Request, db: Session) -> RedirectResponse:
    params = request.query_params
    action = params.get("list_action")
    if action == "create":
        ingredient_list = create_ingredient_list(db, params.get("name") or "New Ingredient List")
        db.commit()
        return RedirectResponse(f"/?view=my-list&list_id={ingredient_list.id}", status_code=303)
    if action == "save":
        try:
            list_id = int(params.get("list_id") or 0)
        except ValueError:
            list_id = 0
        ingredient_list = update_ingredient_list(
            db,
            list_id,
            params.get("name") or "Untitled Ingredient List",
            params.getlist("alcohol"),
            params.getlist("ingredient"),
        )
        db.commit()
        if ingredient_list is None:
            return RedirectResponse("/?view=my-list", status_code=303)
        return RedirectResponse(f"/?view=my-list&list_id={ingredient_list.id}", status_code=303)
    if action == "delete":
        try:
            list_id = int(params.get("list_id") or 0)
        except ValueError:
            list_id = 0
        if list_id:
            delete_ingredient_list(db, list_id)
            db.commit()
        return RedirectResponse("/?view=my-list", status_code=303)
    return RedirectResponse("/?view=my-list", status_code=303)


def _ingredient_list_response(request: Request, db: Session, list_id: int | None = None):
    saved_lists = list_ingredient_lists(db)
    selected = selected_ingredient_list(db, list_id) or (saved_lists[0] if saved_lists else None)
    selected_items = ingredient_list_items(db, selected.id if selected else None)
    catalog = ingredient_catalog(db)
    return templates.TemplateResponse(
        "my_ingredient_list.html",
        {
            "request": request,
            "ingredient_lists": saved_lists,
            "selected_ingredient_list": selected,
            "selected_items": selected_items,
            "alcohol_options": catalog["alcohol"],
            "ingredient_options": catalog["ingredient"],
            "ingredient_list_counts": _ingredient_list_counts(db),
            "root_list_view": True,
        },
    )


@app.head("/")
def home_head():
    return Response(status_code=200)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.head("/healthz")
def healthz_head():
    return Response(status_code=200)


@app.get("/creators")
def creators_page(request: Request, db: Session = Depends(get_db)):
    creators = db.scalars(select(Creator).order_by(Creator.handle)).all()
    return templates.TemplateResponse(
        "creators.html",
        {"request": request, "creators": creators, "creator_stats": _creator_stats(db)},
    )


@app.get("/popular")
@app.get("/popular-cocktails")
@app.get("/top-cocktails")
def popular_page(request: Request, db: Session = Depends(get_db)):
    return _popular_response(request, db)


def _popular_response(request: Request, db: Session):
    creator_rows, creator_metric_title = creator_recipe_sections(db, per_creator=10)
    return templates.TemplateResponse(
        "popular.html",
        {
            "request": request,
            "creator_rows": creator_rows,
            "popular_metric_note": _popular_metric_note(creator_metric_title),
        },
    )


@app.get("/my-list")
@app.get("/my-ingredient-list")
def my_ingredient_list(
    request: Request,
    list_id: str | None = None,
    db: Session = Depends(get_db),
):
    return _ingredient_list_response(request, db, _optional_int(list_id))


@app.post("/my-list/create")
@app.post("/my-ingredient-list/create")
async def create_my_ingredient_list(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    ingredient_list = create_ingredient_list(db, str(form.get("name") or "New Ingredient List"))
    db.commit()
    return RedirectResponse(f"/my-list?list_id={ingredient_list.id}", status_code=303)


@app.post("/my-list/{list_id}/save")
@app.post("/my-ingredient-list/{list_id}/save")
async def save_my_ingredient_list(list_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    ingredient_list = update_ingredient_list(
        db,
        list_id,
        str(form.get("name") or "Untitled Ingredient List"),
        [str(value) for value in form.getlist("alcohol")],
        [str(value) for value in form.getlist("ingredient")],
    )
    db.commit()
    if ingredient_list is None:
        return RedirectResponse("/my-list", status_code=303)
    return RedirectResponse(f"/my-list?list_id={ingredient_list.id}", status_code=303)


@app.post("/my-list/{list_id}/delete")
@app.post("/my-ingredient-list/{list_id}/delete")
def delete_my_ingredient_list(list_id: int, db: Session = Depends(get_db)):
    delete_ingredient_list(db, list_id)
    db.commit()
    return RedirectResponse("/my-list", status_code=303)


@app.get("/gold/{gold_id}")
def gold_detail(gold_id: int, request: Request, db: Session = Depends(get_db)):
    recipe = db.scalar(select(GoldRecipe).where(GoldRecipe.id == gold_id))
    if recipe is None:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    raw_post = db.scalar(select(RawPost).where(RawPost.id == recipe.raw_post_id))
    creator = db.scalar(select(Creator).where(Creator.handle == recipe.creator_handle))
    ingredients = []
    base_spirits = []
    try:
        ingredients = json.loads(recipe.ingredients_json or "[]")
    except json.JSONDecodeError:
        ingredients = []
    try:
        base_spirits = json.loads(recipe.base_spirits_json or "[]")
    except json.JSONDecodeError:
        base_spirits = []
    return templates.TemplateResponse(
        "gold_detail.html",
        {
            "request": request,
            "recipe": recipe,
            "image_url": _media_url(raw_post.local_image_path if raw_post else None),
            "ingredients": ingredients,
            "base_spirits": base_spirits,
            "creator": creator,
            "related_results": related_recipes(db, recipe, limit=6),
        },
    )


def _decorate_result(row: dict) -> dict:
    ingredients = []
    try:
        ingredients = json.loads(row.get("ingredients_json") or "[]")
    except json.JSONDecodeError:
        ingredients = [row.get("ingredients_json")]
    display_ingredients = []
    ingredient_labels: set[str] = set()
    alcohol_labels: set[str] = set()
    for ingredient in ingredients:
        if isinstance(ingredient, dict):
            display_ingredients.append(ingredient.get("raw_text") or ingredient.get("name") or "")
            label = ingredient.get("alcohol_family") or ingredient.get("label") or ingredient.get("normalized_name")
            if label and ingredient.get("category") == "alcohol":
                specific_labels = specific_alcohol_labels(ingredient)
                if specific_labels:
                    alcohol_labels.update(specific_labels)
                else:
                    alcohol_labels.add(str(label).lower())
            elif label and ingredient.get("category") == "ingredient":
                ingredient_labels.add(str(label).lower())
        else:
            display_ingredients.append(ingredient)
    try:
        base_spirits = json.loads(row.get("base_spirits_json") or "[]")
    except json.JSONDecodeError:
        base_spirits = []
    row["ingredients"] = [ingredient for ingredient in display_ingredients if ingredient]
    row["base_spirits"] = [spirit for spirit in base_spirits if spirit]
    row["ingredient_labels"] = ingredient_labels
    row["alcohol_labels"] = alcohol_labels | {str(spirit).lower() for spirit in row["base_spirits"]}
    row["drink_name"] = _display_title(row, row["ingredients"])
    row["detail_path"] = f"/gold/{row['id']}"
    row["image_url"] = _media_url(row.get("local_image_path"))
    row["short_caption"] = (row.get("caption_text") or "")[:220]
    row["show_garnish"] = bool(row.get("garnish") and row.get("garnish") != row.get("method"))
    popularity = row.get("view_count") or row.get("like_count") or row.get("popularity_count")
    row["popularity_label"] = _format_count(popularity)
    return row


def ranked_search_results(
    db: Session,
    query: str,
    alcohol_filters: list[str],
    ingredient_filters: list[str],
    creator_handle: str | None = None,
    limit: int = 60,
) -> list[dict]:
    tokens = [token.lower() for token in query.split() if token.strip()]
    rows = [_decorate_result(row) for row in _active_recipe_rows(db)]
    ranked: list[tuple[float, dict]] = []
    for row in rows:
        if creator_handle and row.get("creator_handle") != creator_handle:
            continue
        if not set(alcohol_filters).issubset(row["alcohol_labels"]):
            continue
        if not set(ingredient_filters).issubset(row["ingredient_labels"]):
            continue
        score = _search_score(row, tokens, query)
        if tokens and score <= 0:
            continue
        score += 30 * len(alcohol_filters) + 26 * len(ingredient_filters)
        score += _popularity_score(row) / 100
        ranked.append((score, row))
    ranked.sort(key=lambda item: (item[0], _popularity_score(item[1]), item[1].get("quality_score") or 0), reverse=True)
    return [row for _score, row in ranked[:limit]]


def ranked_recipes_for_ingredient_list(db: Session, list_id: int, limit: int = 18) -> list[dict]:
    selected = ingredient_list_items(db, list_id)
    selected_items = selected["alcohol"] | selected["ingredient"]
    if not selected_items:
        return []
    ranked: list[tuple[int, int, float, dict]] = []
    for row in [_decorate_result(row) for row in _active_recipe_rows(db)]:
        required_alcohol = row["alcohol_labels"]
        required_ingredients = row["ingredient_labels"]
        required = required_alcohol | required_ingredients
        if not required:
            continue
        missing = sorted(required - selected_items)
        matched = len(required & selected_items)
        if matched == 0:
            continue
        missing_count = len(missing)
        row["availability_status"] = _availability_status(missing_count)
        row["missing_items"] = [display_item_name(item) for item in missing[:6]]
        row["missing_count"] = missing_count
        group = missing_count if missing_count <= 2 else 3
        ranked.append((group, -matched, -_popularity_score(row), row))
    ranked.sort(key=lambda item: (item[0], item[1], item[2], -(item[3].get("quality_score") or 0)))
    return [row for *_rest, row in ranked[:limit]]


def cocktail_of_the_day(db: Session, day: date | None = None) -> dict | None:
    """Return a stable active recipe for a calendar day without assuming contiguous IDs."""
    active_count = _active_recipe_count(db)
    if active_count == 0:
        return None
    current_day = day or date.today()
    day_key = current_day.isoformat()
    offset = sum((index + 1) * ord(char) for index, char in enumerate(day_key)) % active_count
    return _active_recipe_by_offset(db, offset)


def random_recipe(db: Session, offset: int | None = None) -> dict | None:
    active_count = _active_recipe_count(db)
    if active_count == 0:
        return None
    selected_offset = offset if offset is not None else random.SystemRandom().randrange(active_count)
    return _active_recipe_by_offset(db, selected_offset % active_count)


def popular_recipe_results(db: Session, limit: int = 8) -> list[dict]:
    return [_decorate_result(row) for row in _active_recipe_rows(db, limit=limit)]


def featured_creators(db: Session, limit: int = 5) -> list[dict[str, object]]:
    stats = _creator_stats(db)
    creators = db.scalars(select(Creator).order_by(Creator.handle)).all()
    ranked = sorted(
        creators,
        key=lambda creator: (
            stats.get(creator.handle, {}).get("active_recipes", 0),
            creator.display_name or creator.handle,
        ),
        reverse=True,
    )
    cards: list[dict[str, object]] = []
    for creator in ranked[:limit]:
        top_recipe_rows = _active_recipe_rows(db, creator_handle=creator.handle, limit=1)
        cards.append(
            {
                "creator": creator,
                "active_recipes": stats.get(creator.handle, {}).get("active_recipes", 0),
                "top_recipe": _decorate_result(top_recipe_rows[0]) if top_recipe_rows else None,
            }
        )
    return cards


def related_recipes(db: Session, recipe: GoldRecipe, limit: int = 6) -> list[dict]:
    try:
        base_spirits = {str(item).lower() for item in json.loads(recipe.base_spirits_json or "[]")}
    except json.JSONDecodeError:
        base_spirits = set()
    try:
        ingredients = json.loads(recipe.ingredients_json or "[]")
    except json.JSONDecodeError:
        ingredients = []
    ingredient_labels = {
        str(
            ingredient.get("alcohol_family")
            or ingredient.get("label")
            or ingredient.get("normalized_name")
            or ""
        ).lower()
        for ingredient in ingredients
        if isinstance(ingredient, dict)
    }
    target_labels = {item for item in base_spirits | ingredient_labels if item}
    if not target_labels:
        return []
    ranked: list[tuple[int, float, dict]] = []
    for row in [_decorate_result(row) for row in _active_recipe_rows(db)]:
        if row["id"] == recipe.id:
            continue
        labels = row["alcohol_labels"] | row["ingredient_labels"]
        shared = len(labels & target_labels)
        if shared == 0:
            continue
        ranked.append((shared, _popularity_score(row), row))
    ranked.sort(key=lambda item: (item[0], item[1], item[2].get("quality_score") or 0), reverse=True)
    return [row for *_score, row in ranked[:limit]]


def search_suggestions(db: Session, limit: int = 80) -> list[str]:
    suggestions: list[str] = []
    rows = db.execute(
        text(
            """
            SELECT drink_title
            FROM gold_recipes
            WHERE status = 'active' AND drink_title IS NOT NULL AND trim(drink_title) != ''
            ORDER BY COALESCE(view_count, like_count, 0) DESC, COALESCE(quality_score, 0) DESC, id DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).scalars().all()
    for value in rows:
        clean_value = " ".join(str(value).split())
        if clean_value and clean_value not in suggestions:
            suggestions.append(clean_value)
    creators = db.scalars(select(Creator.handle).order_by(Creator.handle)).all()
    for creator in creators:
        label = f"@{creator}"
        if label not in suggestions:
            suggestions.append(label)
    for option in ingredient_catalog(db)["alcohol"][:20]:
        if option.label not in suggestions:
            suggestions.append(option.label)
    return suggestions[:limit]


def creator_recipe_sections(db: Session, per_creator: int = 8) -> tuple[list[dict], str]:
    metric_title = _creator_metric_title(db)
    creators = db.scalars(select(Creator).order_by(Creator.handle)).all()
    rows = []
    for creator in creators:
        recipes = [
            _decorate_result(row)
            for row in _active_recipe_rows(db, creator_handle=creator.handle, limit=per_creator)
        ]
        if recipes:
            rows.append({"creator": creator, "recipes": recipes})
    return rows, metric_title


def popular_classics(db: Session) -> list[dict[str, str | int]]:
    classics = [
        ("Margarita", ["margarita", "tommy s margarita", "tommy's margarita"]),
        ("Old Fashioned", ["old fashioned"]),
        ("Espresso Martini", ["espresso martini", "espresso tini"]),
        ("Mojito", ["mojito"]),
        ("Negroni", ["negroni"]),
        ("Martini", ["martini", "dry martini", "vodka martini"]),
        ("Moscow Mule", ["moscow mule"]),
        ("Daiquiri", ["daiquiri", "hemingway daiquiri"]),
        ("Whiskey Sour", ["whiskey sour", "whisky sour"]),
        ("Aperol Spritz", ["aperol spritz"]),
        ("Painkiller", ["painkiller"]),
        ("Bloody Mary", ["bloody mary"]),
    ]
    rows = db.execute(text("SELECT drink_title_normalized FROM gold_recipes WHERE status = 'active'")).scalars().all()
    titles = [str(title or "") for title in rows]
    links = []
    for label, variants in classics:
        count = sum(1 for title in titles if any(variant in title for variant in variants))
        links.append({"label": label, "href": "/?" + urlencode({"q": label}), "count": count})
    return links


def _active_recipe_rows(db: Session, creator_handle: str | None = None, limit: int | None = None) -> list[dict]:
    params: dict[str, object] = {}
    filters = ["gold_recipes.status = 'active'"]
    if creator_handle:
        filters.append("gold_recipes.creator_handle = :creator_handle")
        params["creator_handle"] = creator_handle
    limit_sql = "LIMIT :limit" if limit else ""
    if limit:
        params["limit"] = limit
    rows = db.execute(
        text(
            f"""
            SELECT
                gold_recipes.*,
                raw_posts.local_image_path,
                COALESCE(gold_recipes.view_count, gold_recipes.like_count, 0) AS popularity_count
            FROM gold_recipes
            JOIN raw_posts ON raw_posts.id = gold_recipes.raw_post_id
            WHERE {" AND ".join(filters)}
            ORDER BY
                COALESCE(gold_recipes.view_count, gold_recipes.like_count, 0) DESC,
                COALESCE(gold_recipes.quality_score, 0) DESC,
                gold_recipes.id DESC
            {limit_sql}
            """
        ),
        params,
    ).mappings().all()
    return [dict(row) for row in rows]


def _active_recipe_count(db: Session) -> int:
    return int(db.scalar(select(func.count(GoldRecipe.id)).where(GoldRecipe.status == "active")) or 0)


def _active_recipe_by_offset(db: Session, offset: int) -> dict | None:
    row = db.execute(
        text(
            """
            SELECT
                gold_recipes.*,
                raw_posts.local_image_path,
                COALESCE(gold_recipes.view_count, gold_recipes.like_count, 0) AS popularity_count
            FROM gold_recipes
            JOIN raw_posts ON raw_posts.id = gold_recipes.raw_post_id
            WHERE gold_recipes.status = 'active'
            ORDER BY gold_recipes.id
            LIMIT 1 OFFSET :offset
            """
        ),
        {"offset": max(offset, 0)},
    ).mappings().first()
    return _decorate_result(dict(row)) if row else None


def _search_score(row: dict, tokens: list[str], raw_query: str) -> float:
    if not tokens:
        return 1
    title = str(row.get("drink_name") or "").lower()
    creator = str(row.get("creator_handle") or "").lower()
    bases = " ".join(row.get("base_spirits") or []).lower()
    ingredients = " ".join([*row.get("ingredients", []), *row.get("ingredient_labels", [])]).lower()
    raw_query = raw_query.lower().strip()
    score = 0.0
    if raw_query and raw_query in title:
        score += 80
    for token in tokens:
        if token in title:
            score += 28
        if token in bases:
            score += 22
        if token in ingredients:
            score += 20
        if token in creator:
            score += 16
    matched_terms = sum(
        1 for token in tokens if token in title or token in bases or token in ingredients or token in creator
    )
    if matched_terms == len(tokens):
        score += 45
    return score


def _popularity_score(row: dict) -> float:
    for key in ("view_count", "like_count", "popularity_count"):
        try:
            value = float(row.get(key) or 0)
        except (TypeError, ValueError):
            value = 0
        if value:
            return value
    return float(row.get("quality_score") or 0)


def _availability_status(missing_count: int) -> str:
    if missing_count == 0:
        return "Can make"
    if missing_count == 1:
        return "Missing 1"
    if missing_count == 2:
        return "Missing 2"
    return "Missing 3+"


def _creator_metric_title(db: Session) -> str:
    view_count, like_count = db.execute(
        text("SELECT count(view_count), count(like_count) FROM gold_recipes WHERE status = 'active'")
    ).one()
    if view_count:
        return "Top Viewed by Creator"
    if like_count:
        return "Most Liked by Creator"
    return "Top Recipes by Creator"


def _popular_metric_note(metric_title: str) -> str:
    if metric_title == "Top Viewed by Creator":
        return "Ranked by real recipe views. Showing up to 10 recipes per creator."
    if metric_title == "Most Liked by Creator":
        return "Ranked by imported likes. Showing up to 10 recipes per creator."
    return "Ranked by the best internal recipe score available. Showing up to 10 recipes per creator."


def _selected_values(request: Request, key: str) -> list[str]:
    values = []
    for value in request.query_params.getlist(key):
        clean_value = " ".join(value.lower().split())
        if clean_value and clean_value not in values:
            values.append(clean_value)
    return values


def _optional_int(value: str | int | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _split_alcohol_options(options: list) -> tuple[list, list]:
    visible_names = ["vodka", "gin", "bourbon", "tequila", "rum", "mezcal"]
    by_name = {option.name: option for option in options}
    visible = [by_name[name] for name in visible_names if name in by_name]
    more = sorted(
        [option for option in options if option.name not in visible_names],
        key=lambda option: (-option.count, option.label),
    )
    return visible, more


def _split_ingredient_options(options: list) -> tuple[list, list]:
    visible_names = ["lemon juice", "lime juice", "orange juice", "mint", "apple", "bitters", "simple syrup", "pineapple juice", "cranberry juice"]
    by_name = {option.name: option for option in options}
    visible = [by_name[name] for name in visible_names if name in by_name]
    fallback = [option for option in sorted(options, key=lambda option: (-option.count, option.label)) if option.name not in visible_names]
    for option in fallback:
        if len(visible) >= 9:
            break
        visible.append(option)
    visible_names = {option.name for option in visible}
    more = sorted(
        [option for option in options if option.name not in visible_names],
        key=lambda option: (-option.count, option.label),
    )
    return visible, more


def _option_cards(request: Request, options: list, selected: list[str], key: str) -> list[dict[str, object]]:
    return [
        {
            "name": option.name,
            "label": option.label,
            "count": option.count,
            "active": option.name in selected,
            "href": _toggle_query_url(request, key, option.name),
        }
        for option in options
    ]


def _active_filter_chips(
    request: Request,
    catalog: dict,
    selected_alcohol: list[str],
    selected_ingredients: list[str],
) -> list[dict[str, str]]:
    labels = {
        option.name: option.label
        for option in [*catalog["alcohol"], *catalog["ingredient"]]
    }
    chips = []
    for key, values in (("alcohol", selected_alcohol), ("ingredient", selected_ingredients)):
        for value in values:
            chips.append(
                {
                    "label": labels.get(value, display_item_name(value)),
                    "href": _remove_query_url(request, key, value),
                }
            )
    return chips


def _toggle_query_url(request: Request, key: str, value: str) -> str:
    current = [(item_key, item_value) for item_key, item_value in request.query_params.multi_items() if item_key != "base"]
    if (key, value) in current:
        current = [item for item in current if item != (key, value)]
    else:
        current.append((key, value))
    return _query_path(current, _request_query_path(request))


def _remove_query_url(request: Request, key: str, value: str) -> str:
    current = [
        (item_key, item_value)
        for item_key, item_value in request.query_params.multi_items()
        if not (item_key == key and item_value == value) and item_key != "base"
    ]
    return _query_path(current, _request_query_path(request))


def _toggle_sort_url(request: Request, key: str) -> str:
    current = [(item_key, item_value) for item_key, item_value in request.query_params.multi_items() if item_key != key]
    if request.query_params.get(key) != "alpha":
        current.append((key, "alpha"))
    return _query_path(current, _request_query_path(request))


def _request_query_path(request: Request) -> str:
    return "/search" if request.url.path == "/search" else "/"


def _query_path(items: list[tuple[str, str]], path: str = "/") -> str:
    cleaned = [(key, value) for key, value in items if value]
    return path + "?" + urlencode(cleaned, doseq=True) if cleaned else path


def _creator_stats(db: Session) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    raw_counts = db.execute(
        select(Creator.handle, func.count(RawPost.id))
        .join(RawPost, RawPost.creator_id == Creator.id, isouter=True)
        .group_by(Creator.handle)
    ).all()
    for handle, count in raw_counts:
        stats.setdefault(handle, {"raw_posts": 0, "active_recipes": 0, "not_recipes": 0})
        stats[handle]["raw_posts"] = int(count or 0)

    gold_counts = db.execute(
        select(GoldRecipe.creator_handle, GoldRecipe.status, func.count(GoldRecipe.id))
        .group_by(GoldRecipe.creator_handle, GoldRecipe.status)
    ).all()
    for handle, status, count in gold_counts:
        stats.setdefault(handle, {"raw_posts": 0, "active_recipes": 0, "not_recipes": 0})
        if status == "active":
            stats[handle]["active_recipes"] = int(count or 0)
        elif status == "not_recipe":
            stats[handle]["not_recipes"] = int(count or 0)
    return stats


def _ingredient_list_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        text(
            """
            SELECT list_id, count(*) AS item_count
            FROM ingredient_list_items
            GROUP BY list_id
            """
        )
    ).mappings().all()
    return {int(row["list_id"]): int(row["item_count"] or 0) for row in rows}


def _display_title(row: dict, ingredients: list[str]) -> str:
    title = (row.get("drink_name") or row.get("drink_title") or "").strip()
    invalid_titles = {"ingredient", "ingredients", "ingredient:", "ingredients:", "method", "method:"}
    if title and title.lower() not in invalid_titles:
        return title
    if ingredients:
        return f"{ingredients[0].split(',')[0][:42]} cocktail"
    return f"Recipe from @{row.get('creator_handle', 'creator')}"


def _format_count(value: int | str | None) -> str:
    if value in (None, ""):
        return ""
    try:
        count = int(value)
    except (TypeError, ValueError):
        return ""
    if count <= 0:
        return ""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def _media_url(local_image_path: str | None) -> str | None:
    if not local_image_path:
        return None
    media_dir = get_settings().media_dir.expanduser().resolve()
    try:
        relative_path = Path(local_image_path).expanduser().resolve().relative_to(media_dir)
    except ValueError:
        return None
    return "/media/" + relative_path.as_posix()
