# Frontend

## Design Goal

The frontend should be simple, dense, and useful. This is an internal workflow tool for indexing and finding cocktail posts, not a landing page.

Use server-rendered pages first. Avoid a separate JavaScript frontend until there is a clear interaction need.

## Pages

## Search Page

Purpose: find indexed cocktail posts.

Expected elements:

- Search input.
- Optional creator filter.
- Result count.
- Search results list.
- Each result shows title when available, creator, likely ingredients, excerpt, and original Instagram link.
- Link to post detail page.

## Import Post Page

Purpose: manually add a post to the index.

Expected fields:

- Creator handle.
- Instagram post URL.
- Pasted caption or visible post text.
- Optional notes.

Expected actions:

- Save post.
- Extract recipe fields.
- Add content to search index.

## Creator List Page

Purpose: manage and inspect creators.

Expected elements:

- Creator handle list.
- Post count per creator.
- Link to creator-specific posts.
- Basic add-creator flow, either here or embedded in import.

## Post Detail Page

Purpose: inspect one indexed post.

Expected elements:

- Creator.
- Original Instagram URL.
- Raw pasted text.
- Extracted drink title.
- Extracted ingredients.
- Extracted instructions or method when available.
- Searchable text fields.
- Created/updated timestamps.

## UI Rules

- Keep navigation obvious.
- Optimize for quick data entry and search.
- Do not add decorative complexity.
- Do not hide original source text.
- Make failed or uncertain extraction visible.
