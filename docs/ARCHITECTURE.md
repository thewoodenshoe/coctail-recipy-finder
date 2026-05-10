# Architecture

## Recommendation

Use a simple server-rendered FastAPI app with SQLite, SQLAlchemy, Jinja templates, SQLite FTS5, pytest, and systemd on Ubuntu.

## Pipeline

The active architecture is:

```text
creator config -> ingestion -> raw_posts -> recipe_extractions -> gold_recipes -> gold_recipe_search_index -> UI/search
```

Ingestion captures source text and metadata. Transformation extracts structured recipe fields. The gold layer stores the current best recipe record. Search and UI read from gold.

## Backend

FastAPI owns:

- HTTP routes.
- Manual caption import.
- Creator visibility.
- Gold recipe search and detail pages.

CLI commands own:

- database initialization
- raw transformation
- gold search rebuild
- creator sync

## Database

SQLite stores:

- creators
- raw source captures
- extraction history
- gold recipes
- gold FTS5 index

Legacy `posts`, `recipes`, and `search_index` are obsolete and should not be reintroduced.

## Ingestion

Supported ingestion paths:

- manual caption import
- creator-provided source text import
- stubbed public provider that does not collect Instagram content

Do not download videos, mirror profiles, store account sessions, or automate around platform access controls.

## Deployment

Production runs on Ubuntu:

- FastAPI under systemd.
- Nightly sync under systemd timer.
- SQLite database in the project `data/` directory.
- Public access through the existing Cloudflare Tunnel.

## Tradeoffs

SQLite and FTS5 are sufficient for the MVP. If data volume, concurrency, or ranking needs outgrow SQLite, revisit PostgreSQL or an external search engine later.
