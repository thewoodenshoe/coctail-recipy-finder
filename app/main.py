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
from app.gold import search_gold_recipes
from app.models import Creator, GoldRecipe, RawPost
from app.services import import_caption_to_gold


app = FastAPI(title="Cocktail Recipe Finder")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.mount("/media", StaticFiles(directory=str(get_settings().media_dir)), name="media")


@app.on_event("startup")
def startup() -> None:
    init_database()


@app.get("/")
def home(request: Request, q: str = "", creator: str = "", db: Session = Depends(get_db)):
    creators = db.scalars(select(Creator).order_by(Creator.handle)).all()
    results = search_gold_recipes(db, q, creator or None)
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "q": q,
            "creator_filter": creator,
            "creators": creators,
            "results": [_decorate_result(row) for row in results],
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
    return row


def _media_url(local_image_path: str | None) -> str | None:
    if not local_image_path:
        return None
    media_dir = get_settings().media_dir.expanduser().resolve()
    try:
        relative_path = Path(local_image_path).expanduser().resolve().relative_to(media_dir)
    except ValueError:
        return None
    return "/media/" + relative_path.as_posix()
