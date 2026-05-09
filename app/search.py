from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Post


def update_post_search_index(session: Session, post: Post) -> None:
    recipe = post.recipe
    ingredients = ""
    if recipe:
        try:
            ingredients = " ".join(json.loads(recipe.ingredients_json or "[]"))
        except json.JSONDecodeError:
            ingredients = recipe.ingredients_json or ""

    tags = " ".join(re.findall(r"#([A-Za-z0-9_]+)", post.caption_text or ""))
    session.execute(text("DELETE FROM search_index WHERE post_id = :post_id"), {"post_id": post.id})
    session.execute(
        text(
            """
            INSERT INTO search_index (
                post_id, creator_handle, source_url, caption_text, drink_name,
                base_spirit, ingredients, method, tags
            )
            VALUES (
                :post_id, :creator_handle, :source_url, :caption_text, :drink_name,
                :base_spirit, :ingredients, :method, :tags
            )
            """
        ),
        {
            "post_id": post.id,
            "creator_handle": post.creator.handle,
            "source_url": post.source_url,
            "caption_text": post.caption_text,
            "drink_name": recipe.drink_name if recipe else "",
            "base_spirit": recipe.base_spirit if recipe else "",
            "ingredients": ingredients,
            "method": recipe.method if recipe else "",
            "tags": tags,
        },
    )


def search_posts(session: Session, query: str = "", creator_handle: str | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"limit": 50}
    filters = []

    if creator_handle:
        filters.append("creators.handle = :creator_handle")
        params["creator_handle"] = creator_handle

    fts_query = build_fts_query(query)
    if fts_query:
        params["fts_query"] = fts_query
        base = """
            SELECT
                posts.id,
                posts.source_url,
                posts.caption_text,
                creators.handle AS creator_handle,
                recipes.drink_name,
                recipes.base_spirit,
                recipes.ingredients_json,
                highlight(search_index, 3, '<mark>', '</mark>') AS excerpt,
                bm25(search_index) AS rank
            FROM search_index
            JOIN posts ON posts.id = search_index.post_id
            JOIN creators ON creators.id = posts.creator_id
            LEFT JOIN recipes ON recipes.post_id = posts.id
            WHERE search_index MATCH :fts_query
        """
        order = "ORDER BY rank, posts.discovered_at DESC LIMIT :limit"
    else:
        base = """
            SELECT
                posts.id,
                posts.source_url,
                posts.caption_text,
                creators.handle AS creator_handle,
                recipes.drink_name,
                recipes.base_spirit,
                recipes.ingredients_json,
                substr(posts.caption_text, 1, 220) AS excerpt,
                0 AS rank
            FROM posts
            JOIN creators ON creators.id = posts.creator_id
            LEFT JOIN recipes ON recipes.post_id = posts.id
            WHERE 1 = 1
        """
        order = "ORDER BY posts.discovered_at DESC LIMIT :limit"

    if filters:
        base += " AND " + " AND ".join(filters)

    rows = session.execute(text(f"{base} {order}"), params).mappings().all()
    return [dict(row) for row in rows]


def build_fts_query(query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())
    return " ".join(tokens)
