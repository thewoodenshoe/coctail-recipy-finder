from __future__ import annotations

import json
import re
from dataclasses import dataclass


BASE_SPIRITS = [
    "gin",
    "bourbon",
    "whiskey",
    "rye",
    "tequila",
    "mezcal",
    "rum",
    "vodka",
    "brandy",
    "cognac",
    "campari",
    "aperol",
]

MEASUREMENT_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d+([./]\d+)?|\.\d+|one|two|three|four|five|six|half|¼|½|¾)\s*"
    r"(oz|ounce|ounces|ml|dash|dashes|barspoon|tsp|tbsp|part|parts)\b",
    re.IGNORECASE,
)
COUNT_INGREDIENT_RE = re.compile(
    r"(?<![A-Za-z0-9])(\d+|one|two|three|four|five|six)\s+"
    r"(egg white|egg|lemon peel|orange peel|lime wedge|mint sprig)\b",
    re.IGNORECASE,
)
METHOD_RE = re.compile(r"\b(shaken|shake|stirred|stir|built|build|blended|blend|muddled|muddle)\b", re.IGNORECASE)
HASHTAG_RE = re.compile(r"#([A-Za-z0-9_]+)")


@dataclass(frozen=True)
class ExtractedRecipe:
    drink_name: str | None
    base_spirit: str | None
    ingredients: list[str]
    method: str | None
    garnish: str | None
    confidence_score: float
    tags: list[str]

    def ingredients_json(self) -> str:
        return json.dumps(self.ingredients, ensure_ascii=True)


def extract_recipe(caption_text: str) -> ExtractedRecipe:
    normalized_text = re.sub(r"�+", "\n", caption_text)
    lines = [line.strip(" -•\t") for line in normalized_text.splitlines() if line.strip()]
    lower_text = normalized_text.lower()

    drink_name = _extract_drink_name(lines)
    base_spirit = _extract_base_spirit(lower_text)
    ingredients = _extract_ingredients(lines)
    method = _extract_method(lines, caption_text)
    garnish = _extract_garnish(lines)
    tags = [tag.lower() for tag in HASHTAG_RE.findall(normalized_text)]

    score = 0.2
    if drink_name:
        score += 0.2
    if base_spirit:
        score += 0.2
    if ingredients:
        score += 0.25
    if method:
        score += 0.1
    if garnish:
        score += 0.05

    return ExtractedRecipe(
        drink_name=drink_name,
        base_spirit=base_spirit,
        ingredients=ingredients,
        method=method,
        garnish=garnish,
        confidence_score=min(score, 0.95),
        tags=tags,
    )


def _extract_drink_name(lines: list[str]) -> str | None:
    first_ingredient_index = next(
        (
            index
            for index, line in enumerate(lines)
            if MEASUREMENT_RE.search(line) or COUNT_INGREDIENT_RE.search(line)
        ),
        None,
    )
    if first_ingredient_index is not None:
        start = max(0, first_ingredient_index - 8)
        for line in reversed(lines[start:first_ingredient_index]):
            candidate = _clean_title_candidate(line)
            if candidate:
                return candidate

    for line in lines[:4]:
        candidate = _clean_title_candidate(line)
        if candidate:
            return candidate
    return None


def _clean_title_candidate(line: str) -> str | None:
    cleaned = line.strip().strip(":")
    if not cleaned:
        return None
    if cleaned.startswith("#") or cleaned.startswith("@"):
        return None
    if MEASUREMENT_RE.search(cleaned) or COUNT_INGREDIENT_RE.search(cleaned):
        return None
    if len(cleaned) > 80:
        return None
    lower = cleaned.lower()
    if lower in {"follow", "following", "log in", "sign up"}:
        return None
    if lower.endswith(" people") or lower == "notjustabartender":
        return None
    cleaned = re.sub(r"^[\"'“”]+|[\"'“”]+$", "", cleaned)
    return cleaned


def _extract_base_spirit(lower_text: str) -> str | None:
    for spirit in BASE_SPIRITS:
        if re.search(rf"\b{re.escape(spirit)}\b", lower_text):
            return spirit
    return None


def _extract_ingredients(lines: list[str]) -> list[str]:
    ingredients: list[str] = []
    for line in lines:
        if MEASUREMENT_RE.search(line) or COUNT_INGREDIENT_RE.search(line):
            ingredients.append(line)
    return ingredients


def _extract_method(lines: list[str], caption_text: str) -> str | None:
    method_lines = [line for line in lines if METHOD_RE.search(line)]
    if method_lines:
        return " ".join(method_lines[:3])
    match = METHOD_RE.search(caption_text)
    return match.group(1).lower() if match else None


def _extract_garnish(lines: list[str]) -> str | None:
    for line in lines:
        if "garnish" in line.lower():
            return line
    return None
