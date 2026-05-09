# Architecture

## Recommendation

Use a simple server-rendered web app:

- FastAPI for backend routes.
- Jinja templates for frontend pages.
- SQLite for storage.
- SQLite FTS5 for search.
- SQLAlchemy for database access.
- systemd for running the service on Ubuntu.
- nginx as a reverse proxy.

This is the right MVP shape because the product is mostly CRUD, text extraction, and search. A separate frontend app, external database, queue, or search cluster would add complexity before the product proves its workflow.

## Components

## Backend

FastAPI owns:

- HTTP routes.
- Form handling.
- Validation.
- Database access.
- Recipe extraction orchestration.
- Search query handling.

## Frontend

Jinja templates provide:

- Search page.
- Import post page.
- Creator list page.
- Post detail page.

Keep the UI plain and task-focused. The user needs fast indexing and search, not a marketing site.

## Database

SQLite stores:

- Creators.
- Posts.
- Extracted recipe fields.
- Search index data through FTS5.

SQLite is acceptable for the MVP because the expected data volume is small and deployment is simpler.

## Ingestion

Start with manual ingestion:

1. User enters creator handle.
2. User enters Instagram post URL.
3. User pastes caption text.
4. App extracts recipe fields.
5. App updates search index.

Do not build scraping first. It is the wrong first risk to take because it is brittle, platform-sensitive, and unnecessary to validate the product.

## Deployment

Target Ubuntu:

- App process managed by systemd.
- nginx proxies HTTP traffic to the local app port.
- SQLite database stored in an application data directory.
- Direct IP access is acceptable for MVP.

## Tradeoffs

- SQLite is simple and reliable for MVP, but may need migration to PostgreSQL if concurrency or multi-user needs grow.
- Jinja is fast to build and easy to deploy, but less interactive than a separate frontend app.
- Manual ingestion is slower for data entry, but avoids scraping risk and proves whether search/indexing is useful.
- FTS5 is built into SQLite and good enough for local text search, but advanced ranking or semantic search may require later additions.
