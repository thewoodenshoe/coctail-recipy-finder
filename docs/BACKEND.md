# Backend

## Responsibilities

The backend provides:

- Creator registry visibility.
- Bulk captured JSONL import.
- Raw post deduplication by source URL.
- Recipe transformation into extraction history.
- Gold recipe promotion.
- Gold recipe search.
- Gold recipe detail pages.

## Routes

- `GET /` - gold recipe search page.
- `GET /?q=...` - gold recipe search results.
- `GET /gold/{gold_id}` - gold recipe detail page.
- `GET /creators` - creator list.

## CLI Commands

- `python -m app.cli init-db`
- `python -m app.cli clear-data`
- `python -m app.cli transform-raw [--creator HANDLE]`
- `python -m app.cli rebuild-gold-search`
- `python -m app.cli sync-creators`
- `python -m app.cli import-jsonl --creator HANDLE --jsonl-file FILE [--replace-creator-data]`

## Service Boundaries

- Creator service: normalize handles and upsert configured creators.
- Ingestion providers: return captured source text and metadata.
- Raw service: upsert raw source records.
- Transformation service: create recipe extraction records.
- Gold service: promote current best extraction to gold recipe.
- Search service: query `gold_recipe_search_index`.

Do not add legacy post/recipe tables back into the active application path.
