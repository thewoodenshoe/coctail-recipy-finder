from __future__ import annotations

import json

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import BASE_DIR
from app.db import get_db, init_database
from app.creators import load_creator_config
from app.models import Creator, Post
from app.search import search_posts
from app.services import import_post


app = FastAPI(title="Cocktail Recipe Finder")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


@app.on_event("startup")
def startup() -> None:
    init_database()


@app.get("/")
def home(request: Request, q: str = "", creator: str = "", db: Session = Depends(get_db)):
    creators = db.scalars(select(Creator).order_by(Creator.handle)).all()
    results = search_posts(db, q, creator or None)
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
        post = import_post(db, creator, source_url, caption_text)
        db.commit()
    except Exception as exc:
        db.rollback()
        return templates.TemplateResponse(
            "import.html",
            {"request": request, "error": str(exc)},
            status_code=400,
        )
    return RedirectResponse(url=f"/posts/{post.id}", status_code=303)


@app.get("/posts/{post_id}")
def post_detail(post_id: int, request: Request, db: Session = Depends(get_db)):
    post = db.scalar(
        select(Post)
        .options(joinedload(Post.creator), joinedload(Post.recipe))
        .where(Post.id == post_id)
    )
    if post is None:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    ingredients = []
    if post.recipe:
        try:
            ingredients = json.loads(post.recipe.ingredients_json or "[]")
        except json.JSONDecodeError:
            ingredients = [post.recipe.ingredients_json]
    return templates.TemplateResponse(
        "post_detail.html",
        {"request": request, "post": post, "ingredients": ingredients},
    )


def _decorate_result(row: dict) -> dict:
    ingredients = []
    try:
        ingredients = json.loads(row.get("ingredients_json") or "[]")
    except json.JSONDecodeError:
        ingredients = [row.get("ingredients_json")]
    row["ingredients"] = ingredients
    row["short_caption"] = (row.get("caption_text") or "")[:220]
    return row
