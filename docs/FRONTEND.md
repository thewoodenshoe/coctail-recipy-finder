# Frontend

## Product Direction

The frontend is a server-rendered cocktail discovery experience. It should feel like a polished cocktail magazine mixed with a practical search app, not an admin table or raw recipe index.

Use the existing FastAPI, Jinja, and CSS stack unless a dependency clearly improves a real interaction. Keep routes and backend contracts stable.

## Design System

- Background: deep charcoal and near-black with subtle warmth.
- Text: warm off-white for primary text, muted warm gray for secondary text.
- Accents: restrained gold, amber, berry, citrus, and a small amount of cool blue for controls.
- Typography: serif display headings plus a clean system sans for body and controls.
- Cards: rounded, image-forward, compact, and editorial. Avoid dense tables and repeated oversized form blocks.
- Motion: subtle hover/tap feedback only, and respect reduced-motion preferences.

## Primary Navigation

- Discover
- Search
- Popular
- Creators
- My Lists

Do not add a permanent random tab. Use the hero/search "Surprise me" action and the Discover "Cocktail of the Day" module instead.

## Discover Page

Purpose: make the product immediately understandable and visually appealing.

Expected elements:

- Supplied Cocktail Finder banner image as the hero.
- Clear headline and concise value proposition.
- Main search bar in the hero.
- Surprise Me action.
- Cocktail of the Day using deterministic daily selection.
- Saved-list matching module.
- Popular Classics.
- Compact browse/filter controls.
- Popular cocktail cards.
- Featured creator cards.

Avoid showing raw methods, sync fields, quality scores, or admin data on homepage cards.

## Search Page

Purpose: find indexed cocktail posts by drink name, ingredient, spirit, bottle, or creator.

Expected elements:

- Dominant search input.
- Filter chips for real database-backed alcohol and ingredients.
- More alcohol/ingredient selectors.
- Active filter summary with Clear all.
- Compact result cards.
- Helpful empty states.

## My Lists

Purpose: manage shared ingredient lists backed by the database.

Expected elements:

- Saved list cards with item counts.
- Create, rename, delete, and save actions.
- Alcohol and ingredient checklist sections generated from recipe data.
- Clear action to find matching cocktails.

This is intentionally not an authentication or ownership feature.

## Popular And Creators

Popular should show top cocktails grouped by creator without horizontal swimlanes. Creator pages should focus on creator cards, recipe counts, and source profile links.

## Cocktail Detail

Purpose: present a recipe cleanly and link back to the source.

Expected elements:

- Title, creator, image or graceful visual fallback.
- Base spirits and metadata where available.
- Ingredients and method in readable sections.
- Separate original recipe link and creator profile link.
- Related cocktails when data supports it.
