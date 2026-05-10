from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BASE_DIR, get_settings
from app.db import get_db, init_database
from app.gold import featured_gold_recipes, search_gold_recipes
from app.models import Creator, GoldRecipe, RawPost
from app.services import import_caption_to_gold


app = FastAPI(title="Cocktail Recipe Finder")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
get_settings().media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.mount("/media", StaticFiles(directory=str(get_settings().media_dir)), name="media")

BASE_SPIRIT_FILTERS = [
    {"label": "Gin", "value": "gin"},
    {"label": "Bourbon", "value": "bourbon"},
    {"label": "Tequila", "value": "tequila"},
    {"label": "Rum", "value": "rum"},
    {"label": "Mezcal", "value": "mezcal"},
    {"label": "Vodka", "value": "vodka"},
]

QUICK_FILTERS = [
    {"label": "Easy", "value": "easy"},
    {"label": "3 ingredients", "value": "three_ingredients"},
    {"label": "Not too sweet", "value": "not_too_sweet"},
    {"label": "Citrusy", "value": "citrusy"},
    {"label": "Bitter", "value": "bitter"},
    {"label": "Summer", "value": "summer"},
    {"label": "Spirit-forward", "value": "spirit_forward"},
]

QUICK_FILTER_TERMS = {
    "easy": {"easy", "simple", "quick", "built"},
    "not_too_sweet": {"not too sweet", "dry", "tart", "acid", "lemon", "lime", "grapefruit"},
    "citrusy": {"citrus", "lemon", "lime", "grapefruit", "orange", "yuzu"},
    "bitter": {"bitter", "bitters", "campari", "aperol", "amaro", "fernet"},
    "summer": {"summer", "tropical", "pineapple", "watermelon", "coconut", "refreshing"},
    "spirit_forward": {"spirit forward", "old fashioned", "martini", "manhattan", "negroni", "stirred"},
}


@app.on_event("startup")
def startup() -> None:
    init_database()


@app.get("/")
def home(
    request: Request,
    q: str = "",
    creator: str = "",
    base: str = "",
    quick: str = "",
    db: Session = Depends(get_db),
):
    creators = db.scalars(select(Creator).order_by(Creator.handle)).all()
    valid_base = _valid_filter_value(base, BASE_SPIRIT_FILTERS)
    valid_quick = _valid_filter_value(quick, QUICK_FILTERS)
    active_search = bool(q or creator or valid_base or valid_quick)
    raw_results = search_gold_recipes(
        db,
        q,
        creator or None,
        valid_base,
        limit=160 if valid_quick else 50,
    )
    decorated_results = [_decorate_result(row) for row in raw_results]
    if valid_quick:
        decorated_results = [row for row in decorated_results if _matches_quick_filter(row, valid_quick)][:50]
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "q": q,
            "creator_filter": creator,
            "base_filter": valid_base,
            "quick_filter": valid_quick,
            "base_spirit_filters": BASE_SPIRIT_FILTERS,
            "quick_filters": QUICK_FILTERS,
            "creators": creators,
            "results": decorated_results if active_search else [],
            "active_search": active_search,
            "featured_gin": [_decorate_result(row) for row in featured_gold_recipes(db, "gin")],
            "featured_bourbon": [_decorate_result(row) for row in featured_gold_recipes(db, "bourbon")],
            "featured_creator": [_decorate_result(row) for row in featured_gold_recipes(db)],
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
        {"request": request, "creators": creators},
    )


@app.get("/import")
def import_page(request: Request):
    return templates.TemplateResponse("import.html", {"request": request, "error": None})


@app.post("/import")
def import_caption(
    request: Request,
    creator: str = Form(...),
    source_url: str = Form(...),
    caption_text: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        recipe = import_caption_to_gold(db, creator, source_url, caption_text)
        db.commit()
    except Exception as exc:
        db.rollback()
        return templates.TemplateResponse(
            "import.html",
            {"request": request, "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse(url=f"/gold/{recipe.id}", status_code=303)


@app.get("/gold/{gold_id}")
def gold_detail(gold_id: int, request: Request, db: Session = Depends(get_db)):
    recipe = db.scalar(select(GoldRecipe).where(GoldRecipe.id == gold_id))
    if recipe is None:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    raw_post = db.scalar(select(RawPost).where(RawPost.id == recipe.raw_post_id))
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
        },
    )


def _decorate_result(row: dict) -> dict:
    ingredients = []
    try:
        ingredients = json.loads(row.get("ingredients_json") or "[]")
    except json.JSONDecodeError:
        ingredients = [row.get("ingredients_json")]
    display_ingredients = []
    for ingredient in ingredients:
        if isinstance(ingredient, dict):
            display_ingredients.append(ingredient.get("raw_text") or ingredient.get("name") or "")
        else:
            display_ingredients.append(ingredient)
    try:
        base_spirits = json.loads(row.get("base_spirits_json") or "[]")
    except json.JSONDecodeError:
        base_spirits = []
    row["ingredients"] = [ingredient for ingredient in display_ingredients if ingredient]
    row["base_spirits"] = [spirit for spirit in base_spirits if spirit]
    row["drink_name"] = row.get("drink_name") or row.get("drink_title")
    row["detail_path"] = f"/gold/{row['id']}"
    row["image_url"] = _media_url(row.get("local_image_path"))
    row["short_caption"] = (row.get("caption_text") or "")[:220]
    row["show_garnish"] = bool(row.get("garnish") and row.get("garnish") != row.get("method"))
    popularity = row.get("view_count") or row.get("like_count") or row.get("popularity_count")
    row["popularity_label"] = _format_count(popularity)
    return row


def _valid_filter_value(value: str, filters: list[dict[str, str]]) -> str:
    values = {item["value"] for item in filters}
    return value if value in values else ""


def _matches_quick_filter(row: dict, quick_filter: str) -> bool:
    if quick_filter == "three_ingredients":
        ingredients = row.get("ingredients") or []
        return 0 < len(ingredients) <= 3
    text = " ".join(
        str(value or "")
        for value in [
            row.get("drink_name"),
            row.get("intro_text"),
            row.get("method"),
            row.get("garnish"),
            " ".join(row.get("ingredients") or []),
            " ".join(row.get("base_spirits") or []),
        ]
    ).lower()
    return any(term in text for term in QUICK_FILTER_TERMS.get(quick_filter, set()))


def _format_count(value: int | str | None) -> str:
    if value in (None, ""):
        return ""
    try:
        count = int(value)
    except (TypeError, ValueError):
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
