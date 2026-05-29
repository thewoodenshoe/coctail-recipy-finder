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


def test_extract_thirstywhale_recipe_ignores_handle_and_maps_jameson():
    caption = """thirstywhale_
Jameson Triple Triple Sour
2 oz Jameson Triple Triple
3/4 oz lemon
1/3 oz orgeat
2 dashes cocoa bitters
3/4 oz egg whites
Dry shake, add ice and shake again, then strain into a coupe glass.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Jameson Triple Triple Sour"
    assert recipe.base_spirits == ["whiskey"]
    assert "2 oz Jameson Triple Triple" in recipe.ingredients
    assert recipe.method is not None
    assert "Dry shake" in recipe.method


def test_extract_thirstywhale_labeled_recipe_keeps_drops_soda_and_full_method():
    caption = """thirstywhale_
Jameson & Ginger
Ingredients:
45 ml Jameson Original
15 ml lime syrup
15 ml ginger syrup
2 drops salt solution
Soda
Stir in a highball glass with ice and top with soda water.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Jameson & Ginger"
    assert "2 drops salt solution" in recipe.ingredients
    assert "Soda" in recipe.ingredients
    assert recipe.method == "Stir in a highball glass with ice and top with soda water."


def test_extract_thirstywhale_made_with_caption_title_and_ingredients():
    caption = """Can you beat the classic espresso tini? I don’t think so.

Yeah, it’s fun to swap things out and get creative—but the classics never die.

This one’s made with Svedka Vodka:
1.5 oz vodka
1.5 oz espresso
0.5 oz coffee liqueur
0.25 oz rich syrup

I don’t do the espresso beans on top… I hit it with a little orange oil instead.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Espresso Tini"
    assert recipe.base_spirits == ["vodka"]
    assert recipe.ingredients == [
        "1.5 oz vodka",
        "1.5 oz espresso",
        "0.5 oz coffee liqueur",
        "0.25 oz rich syrup",
    ]


def test_extract_thirstywhale_recipe_stops_before_explanatory_paragraph():
    caption = """BATCHED PALOMA
20 oz Tequila
10 oz Grapefruit
5 oz Lime
2.5 oz Agave Syrup
2.5 oz Grapefruit Oleo Syrup
2 dashes Salt Solution or not
16 oz Club Soda

It’s beach season, and a tasty Paloma is always a good choice.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Batched Paloma"
    assert "16 oz Club Soda" in recipe.ingredients
    assert "It’s beach season, and a tasty Paloma is always a good choice." not in recipe.ingredients


def test_extract_thirstywhale_keeps_recipe_note_method_out_of_ingredients():
    caption = """Less is more

RED RAIDER
1.5 oz Bourbon
.5 oz Cointreau
.5 oz Real Grenadine
.75 oz Lemon Juice

I think two drops of saline and two drops of absinthe make this drink nice. Always shake hard!
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Red Raider"
    assert recipe.ingredients == [
        "1.5 oz Bourbon",
        ".5 oz Cointreau",
        ".5 oz Real Grenadine",
        ".75 oz Lemon Juice",
    ]
    assert recipe.method == "I think two drops of saline and two drops of absinthe make this drink nice. Always shake hard!"


def test_extract_highproofpreacher_spaced_multiline_title():
    caption = """highproofpreacher
B E T T E R
J U D G E M E N T
—
2 oz Mijenta Tequila Reposado
¾ oz Fresh lemon juice
½ oz Passion Fruit syrup
¾ oz Cynar (float)
Fresh mint

Combine ingredients (except for Cynar) and shake with ice.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Better Judgement"
    assert "2 oz Mijenta Tequila Reposado" in recipe.ingredients
    assert "Fresh mint" in recipe.ingredients
    assert recipe.base_spirits == ["tequila"]


def test_extract_highproofpreacher_numbered_spaced_title():
    caption = """064. G R E E N  E M B E R
O L D  F A S H I O N E D
—
1½ oz Tequila Reposado
¾ oz Green Chile Vodka
¼ oz Passion fruit syrup
4 dashes Aromatic bitters
Lime twist

Combine ingredients and stir with ice.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Green Ember Old Fashioned"
    assert "¾ oz Green Chile Vodka" in recipe.ingredients
    assert recipe.base_spirits == ["tequila", "vodka"]


def test_extract_highproofpreacher_separator_does_not_become_title():
    caption = """Brine & Sunshine
–
1.5 oz Tres Agaves Blanco
¾ oz Carrot juice
½ oz Fresh lime
½ oz pickle brine

Shake with ice, strain over fresh ice.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Brine & Sunshine"
    assert "½ oz pickle brine" in recipe.ingredients


def test_extract_highproofpreacher_dot_delimited_title():
    caption = """Breaking out some refreshing drink recipes.
.
Summer in the Backyard
.
1.5oz gin (@aviationgin)
3/4oz fresh lime juice
1/2oz honey water (@beelocal)
2 strawberries
2dash angostura bitters
Soda
.
Muddle strawberries in a shaker with the honey water & bitters.
.
#highproofpreacher
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Summer in the Backyard"
    assert "1.5oz gin (@aviationgin)" in recipe.ingredients
    assert "Soda" in recipe.ingredients


def test_extract_highproofpreacher_unicode_spacer_title():
    caption = """This cocktail is a slightly smokey Manhattan riff.
⠀⠀⠀⠀⠀⠀⠀⠀⠀
Small Wonder
⠀⠀⠀⠀⠀⠀⠀⠀⠀
2 oz Brandy
¾ oz Amaro
½ oz Smokey Robinson chai syrup
4 dashes cardamom bitters
⠀⠀⠀⠀⠀⠀⠀⠀⠀
Combine ingredients in a mixing glass and stir with ice.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Small Wonder"
    assert "2 oz Brandy" in recipe.ingredients
    assert recipe.base_spirits == ["brandy"]


def test_extract_highproofpreacher_mixed_unicode_fraction_not_title():
    caption = """Minke Martini
⠀⠀⠀⠀⠀⠀⠀⠀⠀
1½ oz Gin
¾ oz blanc vermouth
½ oz amontillado sherry
3 drops sarsaparilla bitters
lemon zest
⠀⠀⠀⠀⠀⠀⠀⠀⠀
Combine gin, vermouth and sherry in a mixing glass and stir with ice.
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Minke Martini"
    assert "1½ oz Gin" in recipe.ingredients
    assert recipe.drink_name != "1½ oz Gin"


def test_extract_multiple_base_spirits():
    caption = """SPLIT BASE SOUR
1 oz gin
1 oz rum
.75 oz lemon juice
Shake with ice.
"""
    recipe = extract_recipe(caption)

    assert recipe.base_spirits == ["gin", "rum"]


def test_base_spirit_prefers_ingredients_over_intro_context():
    caption = """IRISH MAID
This is a riff on a bourbon and cucumber drink.
IRISH MAID
2-3 cucumber slices
.5oz | 15ml simple syrup
.5oz | 15ml elderflower liqueur
.75oz | 22.5ml lemon juice
2oz | 60ml Irish whiskey
In a tin, muddle cucumber pieces, then combine remaining ingredients.
"""
    recipe = extract_recipe(caption)

    assert recipe.base_spirits == ["whiskey"]


def test_extract_join_jules_labeled_ingredients_title():
    caption = """join_jules
•
Follow
Brenton Wood · Great Big Bundle Of Love
Frozen Peach White Wine Mule >>>>
It’s officially time to breakout the blender and start sipping on frozen drinks.
Ingredients:
1 cup white wine
1 cup frozen peaches
Juice of 1 lemon
1/2 cup ginger beer
Blend until smooth & split between two glasses!
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Frozen Peach White Wine Mule"
    assert "Juice of 1 lemon" in recipe.ingredients
    assert "1/2 cup ginger beer" in recipe.ingredients
    assert recipe.method == "Blend until smooth & split between two glasses!"


def test_extract_join_jules_embedded_title_before_ingredients():
    caption = """join_jules
Mother’s Day is this Sunday… do you have your cocktail menu ready?
I’ll be serving one of my mom’s all-time favorites: a French Blonde. But since I’m hosting a few moms this year, I’m batching it in a pitcher ahead of time
Ingredients:
2 cups fresh grapefruit juice
2 cups lillet
1 cup gin
1/2 cup elderflower liqueur
Mix in a pitcher and chill in the fridge until ready to serve
Serve by shaking up 2 at a time using a cocktail shaker
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "French Blonde"
    assert "2 cups lillet" in recipe.ingredients
    assert "1 cup gin" in recipe.ingredients
    assert recipe.base_spirits == ["gin"]
    assert recipe.method is not None
    assert recipe.method.startswith("Mix in a pitcher")


def test_extract_join_jules_fountain_title_skips_audio_line():
    caption = """join_jules
•
Follow
Piero Umiliani · Volto di donna
This is your sign to get the party fountain
Before they sell out, it’s time to add one to cart before your next party.
To your fountain add:
1 jar of olives
1 jar of cocktail onions
1 750 ml bottle of London Dry gin
Splash of dry vermouth
Add a few ice cubes to the bottom, turn it on, and grab a glass!
Xx, happy hosting
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Party Fountain"
    assert "1 jar of olives" in recipe.ingredients
    assert "Splash of dry vermouth" in recipe.ingredients
    assert recipe.base_spirits == ["gin"]
    assert recipe.method == "Add a few ice cubes to the bottom, turn it on, and grab a glass!"


def test_extract_kentuckyginger_mint_julep_unmeasured_block_ingredients():
    caption = """kentuckyginger
MINT JULEP
Handful of mint leaves
1/2 oz simple syrup
2 oz bourbon
lots of crushed ice
Mint for garnish
"""
    recipe = extract_recipe(caption)

    assert recipe.drink_name == "Mint Julep"
    assert "Handful of mint leaves" in recipe.ingredients
    assert "lots of crushed ice" in recipe.ingredients
    assert recipe.garnish == "Mint for garnish"
    assert recipe.base_spirits == ["bourbon"]


def test_cta_post_without_ingredient_block_is_not_recipe():
    caption = """kentuckyginger
Friends don’t let friends drink shitty margs.
Are you still looking for the perfect batched margarita recipe?
Commment “MARGS” and I’ll send you the recipe straight to your inbox.
#cincodemayo #margaritas #tequila #cocktails
"""
    recipe = extract_recipe(caption)

    assert recipe.ingredients == []
