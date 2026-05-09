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
