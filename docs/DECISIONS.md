# Decisions

This file is the architectural decision log. Add new decisions as the project evolves.

## 0001 - Use Manual Caption Ingestion First

Status: Accepted

Decision: The first MVP will allow manual ingestion by creator handle, Instagram post URL, and pasted caption text.

Reasoning: Manual ingestion validates the core product without taking on scraping risk, account risk, platform compliance issues, or brittle automation too early.

Consequences:

- Data entry is slower at first.
- The MVP can be built and tested faster.
- The system preserves source URLs and raw text.
- Later ingestion improvements can be added after the index/search workflow proves useful.

## 0002 - Use FastAPI, SQLite FTS5, SQLAlchemy, Jinja, systemd, and nginx

Status: Accepted

Decision: The default MVP stack is FastAPI, SQLite with FTS5, SQLAlchemy, Jinja templates, systemd, and nginx.

Reasoning: The product is a small internal CRUD/search app. This stack minimizes moving parts while leaving room for clean growth.

Consequences:

- Deployment is straightforward on Ubuntu.
- Search can be implemented without an external search service.
- A separate frontend app is unnecessary for MVP.
- SQLite may need to be replaced later if concurrency, multi-user access, or data size grows significantly.
