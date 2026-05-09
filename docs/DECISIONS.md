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

## 0003 - Use Direct Port 8000 Before nginx or Cloudflare

Status: Accepted

Decision: The first live smoke-test and early MVP serving path will use direct HTTP access on TCP port `8000`.

Reasoning: The existing CHS Finds / CHS Spots deployment already uses nginx, Cloudflare, `80`, `443`, `3000`, `3001`, and `3456`. A separate direct port avoids conflicts while this project is still early.

Consequences:

- Google Home / router forwarding must map external TCP `8000` to the Ubuntu server's TCP `8000`.
- The app must bind to `0.0.0.0:8000` for direct LAN/public testing.
- This is not the final hardened deployment shape.
- nginx/Cloudflare integration can be added later when there is a real app worth fronting.

## 0004 - Ubuntu Is The Production Data Host

Status: Accepted

Decision: Local development is acceptable for coding and unit tests, but production data, ingestion runs, and future Instagram-related collection work should run on Ubuntu.

Reasoning: Keeping production data on the production server avoids drift between local experiments and deployed behavior.

Consequences:

- Future agents should commit, push, and pull on Ubuntu after each completed change set.
- Local test data should be treated as disposable.
- Any real ingestion job must be designed to run safely on Ubuntu.
