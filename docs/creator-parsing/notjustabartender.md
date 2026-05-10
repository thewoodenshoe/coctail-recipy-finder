# notjustabartender Parsing Notes

## Observed Pattern

Sampled reels usually contain:

1. Creator handle and Instagram UI text.
2. Intro/context about the drink, sponsor, inspiration, or story.
3. Cocktail title in mostly uppercase.
4. Ingredient block.
5. Method/instructions.
6. Instagram engagement counts and unrelated recommended content.

The intro/context is useful but should not be displayed as the primary search result excerpt. Store it as `extra_instagram_text`.

## Extraction Rules

- Treat the mostly-uppercase line immediately before the ingredient block as the drink name.
- Convert all-caps drink names to title case for display.
- Treat lines after the title as ingredients until the first method line.
- Ingredient lines may include measurements, gram/cup quantities, counted produce, or short unmeasured items such as `Ginger Beer`.
- Treat method text as the lines after the ingredient block beginning with action words like `Combine`, `In a tin`, `Toast`, or `Serve`.
- If no ingredient block exists, treat the post as non-recipe for index display.

## Sample Corrections

- `DXnYlmJjk48`: `PINK PONY CLUB` -> `Pink Pony Club`.
- `DWXJ28GEfJm`: `MAZAPÀN HORCHATA` -> `Mazapàn Horchata`.
- `DWhdXunAPAH`: `KENTUCKY BUCK` -> `Kentucky Buck`.
- `DWR8lVHluJv`: no recipe block; should not appear in search/index results.
