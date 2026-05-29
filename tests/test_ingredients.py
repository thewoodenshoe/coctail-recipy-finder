from app.ingredients import classify_ingredient, extract_base_spirits_from_ingredients, ingredient_name


def test_ingredient_name_strips_unicode_and_alternate_measures():
    assert ingredient_name("¾ oz fresh lime juice") == "fresh lime juice"
    assert ingredient_name(".66oz | 20ml strawberry syrup") == "strawberry syrup"
    assert ingredient_name("10 mint leaves") == "mint leaves"
    assert ingredient_name("100 proof Bourbon") == "100 proof Bourbon"


def test_classify_brand_names_to_alcohol_families():
    assert classify_ingredient("1/2 ounce Bombay").alcohol_family == "gin"
    assert classify_ingredient("2 oz Four Roses OESO Single Barrel").alcohol_family == "bourbon"
    assert classify_ingredient("500ml Mijenta Reposado").alcohol_family == "tequila"
    assert classify_ingredient("1.5oz gin (@aviationgin)").alcohol_family == "gin"


def test_classify_non_alcohol_ingredient_labels():
    assert classify_ingredient("3/4 oz Lemon Juice").label == "lemon juice"
    assert classify_ingredient("Fresh mint").label == "mint"
    assert classify_ingredient("1 cup apple cider").label == "apple"


def test_base_spirits_from_ingredients_excludes_bitters():
    ingredients = ["2 oz Bombay", "2 dashes Angostura bitters", "3/4 oz lemon juice"]

    assert extract_base_spirits_from_ingredients(ingredients) == ["gin"]
