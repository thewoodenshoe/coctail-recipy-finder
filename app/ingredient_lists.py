from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.models import GoldRecipe, IngredientList, IngredientListItem


@dataclass(frozen=True)
class IngredientOption:
    name: str
    label: str
    count: int
    item_type: str


def list_ingredient_lists(session: Session) -> list[IngredientList]:
    return list(session.scalars(select(IngredientList).order_by(IngredientList.name, IngredientList.id)).all())


def create_ingredient_list(session: Session, name: str) -> IngredientList:
    clean_name = _clean_list_name(name)
    ingredient_list = IngredientList(name=clean_name)
    session.add(ingredient_list)
    session.flush()
    return ingredient_list


def update_ingredient_list(
    session: Session,
    list_id: int,
    name: str,
    alcohol_items: Iterable[str],
    ingredient_items: Iterable[str],
) -> IngredientList | None:
    ingredient_list = session.get(IngredientList, list_id)
    if ingredient_list is None:
        return None
    ingredient_list.name = _clean_list_name(name)
    ingredient_list.updated_at = datetime.now(timezone.utc)
    session.execute(delete(IngredientListItem).where(IngredientListItem.list_id == list_id))
    for item_type, values in (("alcohol", alcohol_items), ("ingredient", ingredient_items)):
        for item_name in sorted({_clean_item_name(value) for value in values if _clean_item_name(value)}):
            session.add(IngredientListItem(list_id=list_id, item_name=item_name, item_type=item_type))
    session.flush()
    return ingredient_list


def delete_ingredient_list(session: Session, list_id: int) -> None:
    session.execute(delete(IngredientListItem).where(IngredientListItem.list_id == list_id))
    ingredient_list = session.get(IngredientList, list_id)
    if ingredient_list is not None:
        session.delete(ingredient_list)
    session.flush()


def ingredient_list_items(session: Session, list_id: int | None) -> dict[str, set[str]]:
    if not list_id:
        return {"alcohol": set(), "ingredient": set()}
    rows = session.scalars(
        select(IngredientListItem).where(IngredientListItem.list_id == list_id)
    ).all()
    grouped = {"alcohol": set(), "ingredient": set()}
    for row in rows:
        if row.item_type in grouped:
            grouped[row.item_type].add(row.item_name)
    return grouped


def ingredient_catalog(session: Session) -> dict[str, list[IngredientOption]]:
    alcohol_counts: Counter[str] = Counter()
    ingredient_counts: Counter[str] = Counter()
    rows = session.execute(
        text(
            """
            SELECT base_spirits_json, ingredients_json
            FROM gold_recipes
            WHERE status = 'active'
            """
        )
    ).mappings().all()
    for row in rows:
        recipe_alcohol: set[str] = set(_json_list(row.get("base_spirits_json")))
        recipe_ingredients: set[str] = set()
        for ingredient in _json_value(row.get("ingredients_json"), []):
            if not isinstance(ingredient, dict):
                continue
            category = ingredient.get("category")
            label = ingredient.get("alcohol_family") or ingredient.get("label") or ingredient.get("normalized_name")
            if not label:
                continue
            item_name = str(label).strip().lower()
            if category == "alcohol":
                recipe_alcohol.add(item_name)
            elif category == "ingredient":
                recipe_ingredients.add(item_name)
        alcohol_counts.update(recipe_alcohol)
        ingredient_counts.update(recipe_ingredients)

    return {
        "alcohol": _options_from_counts(alcohol_counts, "alcohol"),
        "ingredient": _options_from_counts(ingredient_counts, "ingredient"),
    }


def selected_ingredient_list(session: Session, list_id: int | None) -> IngredientList | None:
    if not list_id:
        return None
    return session.get(IngredientList, list_id)


def display_item_name(item_name: str) -> str:
    overrides = {
        "lemon juice": "Lemon",
        "lime juice": "Lime",
        "orange juice": "Orange",
        "grapefruit juice": "Grapefruit",
        "pineapple juice": "Pineapple",
        "cranberry juice": "Cranberry",
        "pomegranate juice": "Pomegranate",
        "soda water": "Soda Water",
        "non-alcoholic aperitif": "Non-Alcoholic Aperitif",
    }
    return overrides.get(item_name, item_name.replace("-", " ").title())


def _options_from_counts(counts: Counter[str], item_type: str) -> list[IngredientOption]:
    return [
        IngredientOption(name=name, label=display_item_name(name), count=count, item_type=item_type)
        for name, count in sorted(counts.items(), key=lambda item: item[0])
        if name
    ]


def _clean_list_name(name: str) -> str:
    clean_name = " ".join((name or "").split())
    return clean_name[:255] or "Untitled Ingredient List"


def _clean_item_name(name: str) -> str:
    return " ".join((name or "").strip().lower().split())[:255]


def _json_value(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _json_list(value: str | None) -> list[str]:
    parsed = _json_value(value, [])
    if not isinstance(parsed, list):
        return []
    return [str(item).strip().lower() for item in parsed if str(item).strip()]
