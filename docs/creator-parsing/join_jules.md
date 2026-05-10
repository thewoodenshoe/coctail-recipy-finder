# join_jules Parsing Notes

## Observed Pattern

Sampled posts use a softer editorial format than `notjustabartender`.

Common recipe posts contain:

1. Creator handle and Instagram UI text.
2. Music/audio attribution.
3. Natural-case drink title or a sentence naming the drink.
4. A labeled ingredient section such as `Ingredients:` or `To your fountain add:`.
5. One or more method lines after the ingredients.
6. Engagement counts, comments, or unrelated recommended content.

## Extraction Rules

- Treat `Ingredients:` and `To your ... add:` as strong recipe-block labels.
- Use the nearest useful line above the label as the drink title.
- If the title is embedded in prose, extract the cocktail phrase when obvious, for example `a French Blonde`.
- Remove decorative trailing arrows such as `>>>>` from titles.
- Accept contextual ingredient lines inside a labeled block, including `Juice of 1 lemon`, `Splash of dry vermouth`, olives, cocktail onions, wine, and ginger beer.
- Treat method lines beginning with `Blend`, `Mix`, `Serve`, or `Add a few ice` as method text after the ingredient block.
- Do not promote roundup posts or CTA-only posts into active gold recipes.

## Sample Corrections

- `DQzak3TD_Rx`: fountain/martini-style recipe; title comes from the line above `To your fountain add:`.
- `DYIEYY_Kt66`: `Frozen Peach White Wine Mule >>>>` -> `Frozen Peach White Wine Mule`.
- `DYA_UEfP1fo`: prose mentions `a French Blonde`; extract `French Blonde` as the title.
- `DYGP4InnTca`: roundup post; should not be active as a recipe.
- `DYDUKPOS7ij`: CTA-only recipe teaser; should not be active as a recipe.
