from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


AMOUNT_TOKEN = (
    r"(?:\d+\s*[-/]\s*\d+|\d+\s*[¼½¾⅓⅔⅛⅜⅝⅞]|\d+(?:\.\d+)?|\.\d+|"
    r"[¼½¾⅓⅔⅛⅜⅝⅞]|one|two|three|four|five|six|seven|eight|nine|ten|half)"
)
UNIT_TOKEN = (
    r"(?:ounces|ounce|oz\.|oz|milliliters|milliliter|ml|cups|cup|grams|gram|g|dashes|dash|"
    r"drops|drop|barspoons|barspoon|teaspoons|teaspoon|tablespoons|tablespoon|tsp|tbsp|"
    r"part|parts)"
)
LEADING_MEASURE_RE = re.compile(
    rf"^\s*{AMOUNT_TOKEN}\s*(?:-\s*{AMOUNT_TOKEN}\s*)?(?:{UNIT_TOKEN})?\s*(?:of\s+)?",
    re.IGNORECASE,
)
ALT_MEASURE_RE = re.compile(rf"^\s*\|\s*{AMOUNT_TOKEN}\s*(?:{UNIT_TOKEN})?\s*", re.IGNORECASE)
NOISE_RE = re.compile(r"[^\w\s&'+-]", re.IGNORECASE)


@dataclass(frozen=True)
class IngredientClassification:
    category: str
    label: str | None
    alcohol_family: str | None = None


ALCOHOL_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("gin", ("gin", "london dry", "bombay", "tanqueray", "beefeater", "plymouth", "aviation", "hendrick", "monkey 47", "roku", "empress", "empress1908gin", "thebotanistgin", "botanist", "nolet")),
    ("bourbon", ("bourbon", "four roses", "fourrosesbourbon", "woodford", "buffalo trace", "maker's mark", "makers mark", "wild turkey", "bulleit bourbon", "bulleitwhiskey", "knob creek", "old forester", "coopers craft", "coopers' craft")),
    ("rye", ("rye", "rye whiskey", "rye whisky", "rittenhouse", "whistlepig", "sazerac rye", "redemptionwhiskey")),
    ("whiskey", ("whiskey", "whisky", "jameson", "irish whiskey", "irish whisky", "scotch", "johnnie walker", "dewars", "dewar's", "jackdaniels", "jack daniels", "laphroaig", "stranahans", "monkey shoulder", "blue peak")),
    ("tequila", ("tequila", "mijenta", "espolon", "patron", "patrón", "don julio", "casamigos", "lalo", "tapatio", "herradura")),
    ("mezcal", ("mezcal", "del maguey", "banhez", "banhezmezcalartesanal", "montelobos", "vida mezcal")),
    ("rum", ("rum", "rhum", "cachaca", "cachaça", "clairin", "clairinthespiritofhaiti", "bacardi", "plantation", "planteray", "appleton", "smith & cross", "smith and cross", "wray", "havana club", "flor de cana", "flor de caña", "diplomatico", "cruzan", "goslings", "mount gay")),
    ("vodka", ("vodka", "tito's", "titos", "ketel one", "absolut", "grey goose")),
    ("brandy", ("brandy", "apple brandy", "pear brandy", "calvados", "armagnac")),
    ("cognac", ("cognac", "hennessy", "courvoisier", "remy martin", "rémy martin", "pierre ferrand")),
    ("pisco", ("pisco",)),
    ("campari", ("campari", "campariofficial")),
    ("aperol", ("aperol", "aperolusa")),
    ("cynar", ("cynar", "cynarusa")),
    ("vermouth", ("vermouth", "punt e mes", "carpano", "dolin", "cocchi", "antica formula")),
    ("sherry", ("sherry", "fino", "oloroso", "amontillado", "manzanilla")),
    ("chartreuse", ("chartreuse", "charteuse")),
    ("absinthe", ("absinthe",)),
    ("aquavit", ("aquavit",)),
    ("amaro", ("amaro", "amaromontenegro", "averna", "montenegro", "fernet", "nonino", "meletti", "zucca", "china china", "antiquepelinkovac", "genepy", "braulio")),
    ("liqueur", ("liqueur", "curacao", "curaçao", "cointreau", "grand marnier", "triple sec", "st germain", "st-germain", "maraschino", "falernum", "allspice dram", "benedictine", "bénédictine", "creme de", "crème de", "kahlua", "giffard", "licor 43", "suze", "amaretto", "drambuie", "jager", "pimms", "pimm s", "cherry herring", "luxardo bitter bianco", "bitter bianco", "banane du bresil", "banane du brasil", "salers")),
    ("wine", ("wine", "champagne", "prosecco", "sparkling rose", "sparkling rosé", "lillet", "port", "madeira")),
    ("beer", ("beer of your choice", "pilsner", "lager", "ipa", "stout", "ale", "hard cider")),
)

BASE_FILTER_FAMILIES = {
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
}

INGREDIENT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("lemon juice", ("lemon juice", "fresh lemon juice", "fresh lemon", "lemon")),
    ("lime juice", ("lime juice", "fresh lime juice", "fresh lime", "lime")),
    ("grapefruit juice", ("grapefruit juice", "grapefruit")),
    ("orange juice", ("orange juice", "fluffy oj")),
    ("pineapple juice", ("pineapple juice", "pineapple")),
    ("apple", ("apple", "apple cider")),
    ("mint", ("mint",)),
    ("simple syrup", ("simple syrup", "simple")),
    ("demerara syrup", ("demerara syrup", "2:1 demerara")),
    ("honey syrup", ("honey syrup",)),
    ("agave syrup", ("agave syrup", "agave nectar", "agave")),
    ("cinnamon syrup", ("cinnamon syrup",)),
    ("ginger syrup", ("ginger syrup", "honey ginger syrup", "honey-ginger syrup")),
    ("passion fruit syrup", ("passion fruit syrup", "passionfruit syrup")),
    ("cane syrup", ("rich cane syrup", "cane syrup")),
    ("rich syrup", ("rich syrup", "2:1 syrup")),
    ("maple syrup", ("maple syrup",)),
    ("fruit syrup", ("cranberry syrup", "pineapple syrup", "guava syrup")),
    ("syrup", ("syrup",)),
    ("orgeat", ("orgeat",)),
    ("grenadine", ("grenadine",)),
    ("bitters", ("bitters", "angostura", "peychaud")),
    ("egg white", ("egg white", "egg whites")),
    ("whole egg", ("whole egg",)),
    ("egg yolk", ("egg yolk", "egg yolks")),
    ("cream", ("cream", "milk", "half and half")),
    ("espresso", ("espresso", "coffee")),
    ("soda water", ("soda water", "club soda", "soda")),
    ("tonic water", ("tonic",)),
    ("ginger beer", ("ginger beer",)),
    ("coconut cream", ("coco lopez", "coconut cream")),
    ("acid blend", ("supasawa",)),
    ("non-alcoholic aperitif", ("ghia", "dr zero zero", "lyre", "lyre s", "lyres", "free spirit aperitif")),
    ("cucumber", ("cucumber",)),
    ("strawberry", ("strawberry", "strawberries")),
    ("orange peel", ("orange peel", "orange twist")),
    ("orange oil", ("orange oil",)),
    ("lemon peel", ("lemon peel", "lemon twist", "lemon zest")),
    ("salt", ("salt", "saline")),
    ("water", ("water",)),
    ("sugar", ("sugar",)),
    ("vanilla extract", ("vanilla extract",)),
    ("almond extract", ("almond extract",)),
    ("ginger", ("ginger",)),
    ("cinnamon", ("cinnamon",)),
    ("nutmeg", ("nutmeg",)),
    ("clove", ("clove", "cloves")),
    ("carrot juice", ("carrot juice",)),
    ("cranberry juice", ("cranberry juice",)),
    ("pomegranate juice", ("pomegranate juice",)),
    ("ice", ("ice",)),
    ("tincture", ("tincture",)),
    ("jalapeno", ("jalapeno", "jalapeño")),
    ("xanthan gum", ("xanthan gum", "xantham gum")),
    ("basil", ("basil",)),
    ("citric acid", ("citric acid",)),
    ("tea", ("tea",)),
    ("honey", ("honey",)),
    ("butter", ("butter",)),
    ("nuts", ("nuts",)),
)


def ingredient_name(raw_text: str) -> str:
    text_value = raw_text.strip(" -•\t")
    if not text_value:
        return raw_text
    if re.match(rf"^\s*{AMOUNT_TOKEN}\s+proof\b", text_value, re.IGNORECASE):
        return text_value
    text_value = LEADING_MEASURE_RE.sub("", text_value, count=1).strip()
    text_value = ALT_MEASURE_RE.sub("", text_value, count=1).strip()
    return text_value.strip(" ,:-") or raw_text


def classify_ingredient(raw_text: str) -> IngredientClassification:
    name = ingredient_name(raw_text)
    searchable = _searchable(name)
    for label, patterns in ALCOHOL_PATTERNS:
        if _matches_any(searchable, patterns):
            return IngredientClassification(category="alcohol", label=label, alcohol_family=label)
    for label, patterns in INGREDIENT_PATTERNS:
        if _matches_any(searchable, patterns):
            return IngredientClassification(category="ingredient", label=label)
    return IngredientClassification(category="unknown", label=None)


def extract_base_spirits_from_ingredients(ingredients: list[str]) -> list[str]:
    found: list[str] = []
    for ingredient in ingredients:
        classification = classify_ingredient(ingredient)
        if classification.alcohol_family in BASE_FILTER_FAMILIES:
            found.append(classification.alcohol_family)
    return _dedupe_by_priority(found)


def extract_base_spirits_from_text(text: str) -> list[str]:
    searchable = _searchable(text)
    found = [
        label
        for label, patterns in ALCOHOL_PATTERNS
        if label in BASE_FILTER_FAMILIES and _matches_any(searchable, patterns)
    ]
    return _dedupe_by_priority(found)


def _matches_any(searchable: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(_searchable(pattern))}\b", searchable) for pattern in patterns)


def _searchable(text_value: str) -> str:
    normalized = unicodedata.normalize("NFKD", text_value.lower()).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace("_", " ").replace("-", " ")
    normalized = NOISE_RE.sub(" ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _dedupe_by_priority(values: list[str]) -> list[str]:
    priority = ["gin", "bourbon", "whiskey", "rye", "tequila", "rum", "mezcal", "vodka", "brandy", "cognac", "campari", "aperol"]
    deduped = _dedupe(values)
    return sorted(deduped, key=lambda value: priority.index(value) if value in priority else len(priority))
