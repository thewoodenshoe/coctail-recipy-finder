from __future__ import annotations

from app.extraction import extract_recipe


def test_extract_recipe_from_caption():
    caption = """Bee's Knees

2 oz gin
3/4 oz lemon juice
3/4 oz honey syrup
Shake with ice and strain.
Garnish with lemon twist.
#gin #cocktail
"""
    recipe = extract_recipe(caption)
    assert recipe.drink_name == "Bee's Knees"
    assert recipe.base_spirit == "gin"
    assert "2 oz gin" in recipe.ingredients
    assert "Shake" in recipe.method
    assert recipe.garnish == "Garnish with lemon twist."
    assert "gin" in recipe.tags


def test_extract_recipe_from_pink_pony_example():
    caption = """PINK PONY CLUB

.25oz | 7.5ml Campari
.66oz | 20ml strawberry syrup
.75oz | 22.5ml lemon juice
1.5oz | 45ml gin
1 egg white

Combine all ingredients into a shaker tin with ice, shake hard for at least 25 seconds to avoid having to dry shake (good luck). Garnish with an expressed lemon peel.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Pink Pony Club"
    assert recipe.base_spirit == "gin"
    assert ".66oz | 20ml strawberry syrup" in recipe.ingredients
    assert "1 egg white" in recipe.ingredients
    assert recipe.method is not None
    assert "shake hard" in recipe.method
    assert recipe.garnish is not None


def test_extract_recipe_title_near_ingredient_block_from_instagram_text():
    caption = """notjustabartender
4 people
A certified platinum banger.
Still delicious though.
PINK PONY CLUB
.25oz | 7.5ml Campari
.66oz | 20ml strawberry syrup
.75oz | 22.5ml lemon juice
1.5oz | 45ml gin
1 egg white��Combine all ingredients into a shaker tin with ice, shake hard.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Pink Pony Club"
    assert recipe.base_spirit == "gin"
    assert "1 egg white" in recipe.ingredients
    assert recipe.extra_instagram_text is not None
    assert "certified platinum" in recipe.extra_instagram_text


def test_extract_notjustabartender_component_recipe_block():
    caption = """notjustabartender
mijentatequila
Let me know if you slap yo’ mama. #ad | @mijentatequila
This has been kicking around my dome for the past 3 or 4 months.
MAZAPÀN HORCHATA
1 cup of long grain rice
2 Mexican cinnamon sticks
2-3 star anise pods
2-3 cloves
.25 cup of sliced almonds
4 cups water
1 cup granulated sugar
360ml evaporated milk
360ml condensed milk
3 Mazapan disks
500ml Mijenta Reposado
Toast rice, spices, and almonds together in a pan on medium to high heat. Store in fridge for up to 2 weeks.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Mazapàn Horchata"
    assert "1 cup of long grain rice" in recipe.ingredients
    assert "500ml Mijenta Reposado" in recipe.ingredients
    assert recipe.method is not None
    assert recipe.method.startswith("Toast rice")
    assert recipe.base_spirits == ["tequila"]


def test_extract_brand_names_to_normalized_base_spirits():
    caption = """KENTUCKY BUCK
3-4 strawberries
.75oz | 22.5ml lemon juice
.75oz | 22.5ml simple syrup
2oz | 60ml Four Roses OESO Single Barrel
Ginger Beer
In a tin, muddle strawberries. Garnish with a strawberry.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Kentucky Buck"
    assert recipe.base_spirit == "bourbon"
    assert recipe.base_spirits == ["bourbon"]


def test_extract_multiple_base_spirits():
    caption = """SPLIT BASE SOUR
1 oz gin
1 oz rum
.75 oz lemon juice
Shake with ice.
"""
    recipe = extract_recipe(caption)

    assert recipe.base_spirits == ["gin", "rum"]
