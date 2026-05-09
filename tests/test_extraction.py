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

    assert recipe.drink_name == "PINK PONY CLUB"
    assert recipe.base_spirit == "campari"
    assert ".66oz | 20ml strawberry syrup" in recipe.ingredients
    assert "1 egg white" in recipe.ingredients
    assert recipe.method is not None
    assert "shake hard" in recipe.method
    assert recipe.garnish is not None
