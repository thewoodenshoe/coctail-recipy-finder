from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.models import GoldRecipe, IngredientList, IngredientListItem


SEEDED_ALCOHOL_OPTIONS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("absinthe", "Absinthe", ("absinthe",)),
    ("allspice dram", "Allspice Dram", ("allspice dram", "pimento dram")),
    ("amaretto", "Amaretto", ("amaretto",)),
    ("amaro", "Amaro", ("amaro",)),
    ("amaro averna", "Amaro Averna", ("amaro averna", "averna")),
    ("amaro montenegro", "Amaro Montenegro", ("amaro montenegro", "montenegro")),
    ("amaro nonino", "Amaro Nonino", ("amaro nonino", "nonino")),
    ("aperol", "Aperol", ("aperol",)),
    ("apricot liqueur", "Apricot Liqueur", ("apricot liqueur", "apricot brandy")),
    ("aquavit", "Aquavit", ("aquavit",)),
    ("benedictine", "Benedictine", ("benedictine")),
    ("blue curacao", "Blue Curacao", ("blue curacao")),
    ("brandy", "Brandy", ("brandy",)),
    ("campari", "Campari", ("campari",)),
    ("chambord", "Chambord", ("chambord", "raspberry liqueur")),
    ("chartreuse", "Chartreuse", ("chartreuse", "charteuse")),
    ("cherry heering", "Cherry Heering", ("cherry heering",)),
    ("coconut liqueur", "Coconut Liqueur", ("coconut liqueur", "malibu")),
    ("coffee liqueur", "Coffee Liqueur", ("coffee liqueur", "kahlua", "mr black")),
    ("cointreau", "Cointreau", ("cointreau",)),
    ("cognac", "Cognac", ("cognac",)),
    ("creme de banane", "Banana Liqueur", ("banana liqueur", "creme de banane", "banane du bresil", "banane du brasil")),
    ("creme de cacao", "Creme De Cacao", ("creme de cacao", "cocoa liqueur")),
    ("creme de cassis", "Creme De Cassis", ("creme de cassis", "cassis")),
    ("creme de menthe", "Creme De Menthe", ("creme de menthe")),
    ("creme de violette", "Creme De Violette", ("creme de violette")),
    ("curacao", "Curacao", ("curacao")),
    ("cynar", "Cynar", ("cynar",)),
    ("drambuie", "Drambuie", ("drambuie",)),
    ("falernum", "Falernum", ("falernum",)),
    ("fernet branca", "Fernet-Branca", ("fernet branca", "fernet-branca", "fernet")),
    ("frangelico", "Frangelico", ("frangelico", "hazelnut liqueur")),
    ("ginger liqueur", "Ginger Liqueur", ("ginger liqueur", "domaine de canton")),
    ("grand marnier", "Grand Marnier", ("grand marnier",)),
    ("green chartreuse", "Green Chartreuse", ("green chartreuse",)),
    ("italicus", "Italicus", ("italicus", "bergamot liqueur")),
    ("jagermeister", "Jagermeister", ("jagermeister", "jager")),
    ("licor 43", "Licor 43", ("licor 43",)),
    ("lillet blanc", "Lillet Blanc", ("lillet blanc", "lillet")),
    ("luxardo bitter bianco", "Luxardo Bitter Bianco", ("luxardo bitter bianco", "bitter bianco")),
    ("maraschino liqueur", "Maraschino Liqueur", ("maraschino liqueur", "maraschino", "luxardo maraschino")),
    ("orange liqueur", "Orange Liqueur", ("orange liqueur",)),
    ("pastis", "Pastis", ("pastis", "pernod")),
    ("peach liqueur", "Peach Liqueur", ("peach liqueur", "peach schnapps")),
    ("pisco", "Pisco", ("pisco",)),
    ("pimms", "Pimm's", ("pimms", "pimm s", "pimm's")),
    ("rye", "Rye", ("rye", "rye whiskey", "rye whisky")),
    ("sloe gin", "Sloe Gin", ("sloe gin",)),
    ("st germain", "St Germain", ("st germain", "st-germain", "stgermaindrinks", "elderflower liqueur")),
    ("sambuca", "Sambuca", ("sambuca",)),
    ("scotch", "Scotch", ("scotch",)),
    ("sherry", "Sherry", ("sherry", "fino", "oloroso", "amontillado", "manzanilla")),
    ("suze", "Suze", ("suze",)),
    ("sweet vermouth", "Sweet Vermouth", ("sweet vermouth", "vermouth rosso", "carpano antica", "antica formula")),
    ("triple sec", "Triple Sec", ("triple sec",)),
    ("vermouth", "Vermouth", ("vermouth",)),
    ("yellow chartreuse", "Yellow Chartreuse", ("yellow chartreuse",)),
)


@dataclass(frozen=True)
class IngredientOption:
    name: str
    label: str
    count: int
    item_type: str


CatalogRevisionKey = tuple[int, str, int, int, str]

_CATALOG_CACHE: dict[CatalogRevisionKey, dict[str, list[IngredientOption]]] = {}
_CATALOG_CACHE_MAX_ENTRIES = 8


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
    revision_key = _catalog_revision_key(session)
    cached_catalog = _CATALOG_CACHE.get(revision_key)
    if cached_catalog is not None:
        return cached_catalog

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
                specific_labels = specific_alcohol_labels(ingredient)
                if specific_labels:
                    recipe_alcohol.update(specific_labels)
                else:
                    recipe_alcohol.add(item_name)
            elif category == "ingredient":
                recipe_ingredients.add(item_name)
        alcohol_counts.update(recipe_alcohol)
        ingredient_counts.update(recipe_ingredients)
    for name, _label, _patterns in SEEDED_ALCOHOL_OPTIONS:
        alcohol_counts.setdefault(name, 0)

    catalog = {
        "alcohol": _options_from_counts(alcohol_counts, "alcohol"),
        "ingredient": _options_from_counts(ingredient_counts, "ingredient"),
    }
    _CATALOG_CACHE[revision_key] = catalog
    while len(_CATALOG_CACHE) > _CATALOG_CACHE_MAX_ENTRIES:
        _CATALOG_CACHE.pop(next(iter(_CATALOG_CACHE)))
    return catalog


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
    overrides.update({name: label for name, label, _patterns in SEEDED_ALCOHOL_OPTIONS})
    return overrides.get(item_name, item_name.replace("-", " ").title())


def specific_alcohol_labels(ingredient: dict) -> set[str]:
    searchable = _searchable_text(
        " ".join(
            str(ingredient.get(key) or "")
            for key in ("raw_text", "name", "normalized_name", "label", "alcohol_family")
        )
    )
    labels = set()
    for name, _label, patterns in SEEDED_ALCOHOL_OPTIONS:
        if any(_phrase_in_text(_searchable_text(pattern), searchable) for pattern in patterns):
            labels.add(name)
    return labels


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


def _searchable_text(value: str) -> str:
    return " ".join(
        (value or "")
        .lower()
        .replace("&", " and ")
        .replace("_", " ")
        .replace("-", " ")
        .replace("'", " ")
        .split()
    )


def _phrase_in_text(phrase: str, searchable: str) -> bool:
    if not phrase:
        return False
    return f" {phrase} " in f" {searchable} "


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


def _catalog_revision_key(session: Session) -> CatalogRevisionKey:
    count, max_id, max_transformed_at = session.execute(
        text(
            """
            SELECT
                count(*) AS active_count,
                COALESCE(max(id), 0) AS max_id,
                COALESCE(max(transformed_at), '') AS max_transformed_at
            FROM gold_recipes
            WHERE status = 'active'
            """
        )
    ).one()
    bind = session.get_bind()
    return (
        id(bind),
        str(bind.url),
        int(count or 0),
        int(max_id or 0),
        str(max_transformed_at or ""),
    )
