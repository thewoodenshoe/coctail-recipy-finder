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

BRAND_SPIRIT_MAP = {
    "four roses": "bourbon",
    "four roses oeso": "bourbon",
    "mijenta": "tequila",
    "mijenta tequila": "tequila",
    "mijenta reposado": "tequila",
    "mijenta tequila blanco": "tequila",
    "luxardo del santo": "herbal liqueur",
    "angostura": "bitters",
}

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
RECIPE_LABEL_RE = re.compile(r"^(ingredients|to your .* add|to .* add)\s*:?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractedRecipe:
    drink_name: str | None
    base_spirit: str | None
    base_spirits: list[str]
    ingredients: list[str]
    method: str | None
    garnish: str | None
    extra_instagram_text: str | None
    confidence_score: float
    tags: list[str]

    def ingredients_json(self) -> str:
        return json.dumps(self.ingredients, ensure_ascii=True)

    def base_spirits_json(self) -> str:
        return json.dumps(self.base_spirits, ensure_ascii=True)


def extract_recipe(caption_text: str) -> ExtractedRecipe:
    normalized_text = re.sub(r"�+", "\n", caption_text)
    lines = [line.strip(" -•\t") for line in normalized_text.splitlines() if line.strip()]
    lower_text = normalized_text.lower()

    recipe_block = _find_recipe_block(lines)
    scoped_lines = recipe_block.recipe_lines if recipe_block else lines

    drink_name = recipe_block.drink_name if recipe_block else _extract_drink_name(lines)
    ingredients = _extract_ingredients(scoped_lines, recipe_block)
    base_source_text = "\n".join([*ingredients, drink_name or ""])
    base_spirits = _extract_base_spirits(base_source_text)
    if not base_spirits:
        base_spirits = _extract_base_spirits(lower_text)
    base_spirit = base_spirits[0] if base_spirits else None
    method = _extract_method(scoped_lines, normalized_text, recipe_block)
    garnish = _extract_garnish(scoped_lines)
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
        base_spirits=base_spirits,
        ingredients=ingredients,
        method=method,
        garnish=garnish,
        extra_instagram_text=recipe_block.extra_instagram_text if recipe_block else None,
        confidence_score=min(score, 0.95),
        tags=tags,
    )


@dataclass(frozen=True)
class RecipeBlock:
    drink_name: str
    recipe_lines: list[str]
    ingredient_lines: list[str]
    method_lines: list[str]
    extra_instagram_text: str | None


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


def _find_recipe_block(lines: list[str]) -> RecipeBlock | None:
    labeled_block = _find_labeled_recipe_block(lines)
    if labeled_block:
        return labeled_block

    for title_index, line in enumerate(lines):
        title = _clean_title_candidate(line)
        if not title or not _looks_like_recipe_title(line):
            continue

        following = lines[title_index + 1 :]
        if not any(_looks_like_ingredient_line(candidate) for candidate in following[:14]):
            continue

        ingredient_lines: list[str] = []
        method_lines: list[str] = []
        in_method = False
        for candidate_index, candidate in enumerate(following):
            if _is_instagram_tail_line(candidate):
                break
            if candidate.startswith("#"):
                break
            if not in_method and _looks_like_method_start(candidate) and ingredient_lines:
                in_method = True
            if in_method:
                method_lines.append(candidate)
                continue
            upcoming = following[candidate_index + 1 : candidate_index + 4]
            if (
                _looks_like_ingredient_line(candidate)
                or ingredient_lines
                or (
                    _looks_like_contextual_ingredient_line(candidate)
                    and any(_looks_like_ingredient_line(line) for line in upcoming)
                )
            ):
                ingredient_lines.append(candidate)

        ingredient_lines = [line for line in ingredient_lines if not _looks_like_method_start(line)]
        if not ingredient_lines:
            continue

        return RecipeBlock(
            drink_name=_title_case(title),
            recipe_lines=[title, *ingredient_lines, *method_lines],
            ingredient_lines=ingredient_lines,
            method_lines=method_lines,
            extra_instagram_text="\n".join(lines[:title_index]).strip() or None,
        )
    return None


def _find_labeled_recipe_block(lines: list[str]) -> RecipeBlock | None:
    for label_index, line in enumerate(lines):
        if not RECIPE_LABEL_RE.search(line):
            continue

        title = _title_before_label(lines, label_index)
        if not title:
            continue

        ingredient_lines: list[str] = []
        method_lines: list[str] = []
        in_method = False
        for candidate in lines[label_index + 1 :]:
            if _is_instagram_tail_line(candidate) or candidate.startswith("#"):
                break
            if _looks_like_method_start(candidate) and ingredient_lines:
                in_method = True
            if in_method:
                method_lines.append(candidate)
                continue
            if _looks_like_ingredient_line(candidate) or _looks_like_contextual_ingredient_line(candidate):
                ingredient_lines.append(candidate)
                continue
            if ingredient_lines:
                break

        ingredient_lines = [line for line in ingredient_lines if not _looks_like_method_start(line)]
        if len(ingredient_lines) < 2:
            continue

        return RecipeBlock(
            drink_name=title,
            recipe_lines=[title, *ingredient_lines, *method_lines],
            ingredient_lines=ingredient_lines,
            method_lines=method_lines,
            extra_instagram_text="\n".join(lines[:label_index]).strip() or None,
        )
    return None


def _title_before_label(lines: list[str], label_index: int) -> str | None:
    window = lines[max(0, label_index - 8) : label_index]
    for line in window:
        party_fountain = re.search(r"\b(?:get|bring|use)\s+the\s+([A-Za-z\s]+fountain)\b", line, re.IGNORECASE)
        if party_fountain:
            return party_fountain.group(1).strip().title()
    for line in reversed(window):
        embedded = _extract_embedded_drink_title(line)
        if embedded:
            return _title_case(embedded)
        candidate = _clean_title_candidate(line)
        if not candidate or _is_creator_or_ui_line(candidate):
            continue
        if _looks_like_sentence_context(candidate):
            continue
        if ">>" in candidate:
            candidate = re.sub(r"\s*>+\s*$", "", candidate).strip()
        return _title_case(candidate)
    return None


def _extract_embedded_drink_title(line: str) -> str | None:
    match = re.search(r"\ba\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,4})\b", line)
    if match:
        return match.group(1).strip(" .!")
    return None


def _looks_like_sentence_context(line: str) -> bool:
    lower = line.lower()
    if " · " in line:
        return True
    if len(line) > 64:
        return True
    return any(
        phrase in lower
        for phrase in (
            "this is your sign",
            "it’s officially",
            "it's officially",
            "do you have",
            "i’ll be serving",
            "i'll be serving",
            "comment ",
        )
    )


def _looks_like_recipe_title(line: str) -> bool:
    letters = [char for char in line if char.isalpha()]
    if not letters:
        return False
    uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
    return uppercase_ratio >= 0.7 and len(line) <= 64


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
    if _is_creator_or_ui_line(lower):
        return None
    if lower.endswith(" people"):
        return None
    cleaned = re.sub(r"^[\"'“”]+|[\"'“”]+$", "", cleaned)
    return cleaned


def _is_creator_or_ui_line(line: str) -> bool:
    lower = line.lower().strip()
    return lower in {
        "follow",
        "following",
        "log in",
        "sign up",
        "notjustabartender",
        "join_jules",
        "kentuckyginger",
    }


def _extract_base_spirit(lower_text: str) -> str | None:
    spirits = _extract_base_spirits(lower_text)
    return spirits[0] if spirits else None


def _extract_base_spirits(text: str) -> list[str]:
    lower_text = text.lower()
    found: list[str] = []
    for spirit in BASE_SPIRITS:
        if re.search(rf"\b{re.escape(spirit)}\b", lower_text):
            found.append(spirit)
    for brand, spirit in BRAND_SPIRIT_MAP.items():
        if re.search(rf"\b{re.escape(brand)}\b", lower_text):
            found.append(spirit)
    return _dedupe_spirits(found)


def _dedupe_spirits(spirits: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for spirit in spirits:
        if spirit in seen:
            continue
        seen.add(spirit)
        deduped.append(spirit)
    return deduped


def _extract_ingredients(lines: list[str], recipe_block: RecipeBlock | None = None) -> list[str]:
    if recipe_block:
        return recipe_block.ingredient_lines
    ingredients: list[str] = []
    for line in lines:
        if _looks_like_ingredient_line(line):
            ingredients.append(line)
    return ingredients


def _extract_method(
    lines: list[str],
    caption_text: str,
    recipe_block: RecipeBlock | None = None,
) -> str | None:
    if recipe_block and recipe_block.method_lines:
        return " ".join(recipe_block.method_lines)
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


def _looks_like_ingredient_line(line: str) -> bool:
    lower = line.lower()
    if MEASUREMENT_RE.search(line) or COUNT_INGREDIENT_RE.search(line):
        return True
    if re.search(r"(?<![A-Za-z0-9])\d+(-\d+)?\s*(g|grams|cup|cups)\b", lower):
        return True
    if re.search(r"(?<![A-Za-z0-9])\d+(-\d+)?\s+(slices?|pods?|cloves?|disks?|strawberries|cucumber slices?)\b", lower):
        return True
    return lower in {"ginger beer", "angostura® aromatic bitters, to top"}


def _looks_like_contextual_ingredient_line(line: str) -> bool:
    lower = line.lower()
    if _looks_like_sentence_context(line):
        return False
    if re.search(r"[.!?]", line) and not re.search(r"^(juice of|splash of|handful of|lots of|mint for garnish)\b", lower):
        return False
    if re.search(r"^(juice of|splash of|handful of|lots of|mint for garnish)\b", lower):
        return True
    if re.search(r"\b(olives|cocktail onions|vermouth|wine|gin|bourbon|tequila|mezcal|rum|vodka|lillet|ginger beer|crushed ice)\b", lower):
        return len(line) <= 80
    return False


def _looks_like_method_start(line: str) -> bool:
    return bool(
        re.search(
            r"^(combine|in a |toast|add ice|add a few ice|mix|serve|store|top with|muddle|dirty dump|strain|blend)",
            line,
            re.IGNORECASE,
        )
    )


def _is_instagram_tail_line(line: str) -> bool:
    lower = line.lower()
    if lower in {"messages", "follow", "meta", "about", "blog", "jobs", "help", "api", "privacy", "terms"}:
        return True
    if lower in {"xx, happy hosting", "happy hosting!!", "cheers!"}:
        return True
    if line == "•":
        return True
    return bool(re.fullmatch(r"[\d,.]+[km]?", lower))


def _title_case(title: str) -> str:
    cleaned = re.sub(r"\s*>+\s*$", "", title).strip()
    if not _looks_like_recipe_title(cleaned):
        return cleaned
    return " ".join(word[:1].upper() + word[1:].lower() for word in cleaned.split())
