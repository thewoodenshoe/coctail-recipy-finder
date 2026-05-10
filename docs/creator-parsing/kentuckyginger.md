# kentuckyginger Parsing Notes

## Observed Pattern

Sampled posts include many lifestyle, intro, travel, and CTA posts mixed with actual cocktail recipes. This creator should be treated as recipe-sparse until a real ingredient block is found.

## Extraction Rules

- Hashtags alone must not create base-spirit matches for active search.
- CTA-only posts such as `Comment MARGS and I’ll send you the recipe` are not recipes unless the ingredient block is present in the captured text.
- Actual recipes may use a simple title followed by ingredients, for example `MINT JULEP`.
- Accept unmeasured ingredient lines inside a detected recipe block when surrounded by measured ingredients, for example `Handful of mint leaves`, `lots of crushed ice`, and `Mint for garnish`.
- Base spirits should come from ingredients first. For `2 oz bourbon`, the base spirit is `bourbon`.
- If comments mention cocktail words, those should remain raw fallback text only and should not promote a post into active gold search.

## Sample Corrections

- `DX11O1-uiSH`: `MINT JULEP` with mint, simple syrup, bourbon, crushed ice, and mint garnish should become an active gold recipe.
- `DX9f0C4uL8a`: CTA-only margarita teaser should remain `not_recipe` unless the actual recipe text is captured later.
