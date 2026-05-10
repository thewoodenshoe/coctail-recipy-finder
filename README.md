# Cocktail Recipe Finder

Cocktail Recipe Finder is an AI-first software project for building a searchable index of cocktail-related Instagram posts from selected cocktail creators.

The product owner should be able to provide creator handles and Instagram post links, then search the indexed content by terms like `gin`, `mezcal`, `negroni`, or `sour`. Search results should show the drink title when known, likely ingredients, extracted text, creator, and the original Instagram post link.

## MVP

The MVP should stay deliberately simple:

- Maintain a list of cocktail creators.
- Manually add an Instagram post URL.
- Paste the caption or visible post text.
- Extract likely recipe fields from the pasted text.
- Store raw source text, extraction history, gold recipe records, and searchable text.
- Search across gold recipes using SQLite FTS5.
- View search results and gold recipe details in a basic web UI.

The default implementation direction is FastAPI, SQLite with FTS5, SQLAlchemy, Jinja templates, systemd, and nginx.

## Running Locally

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Initialize the local database and sync the configured creators:

```bash
.venv/bin/python -m app.cli init-db
.venv/bin/python -m app.cli sync-creators
```

Run the app:

```bash
.venv/bin/uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

Run tests:

```bash
.venv/bin/pytest
```

## Current Features

- Creator registry in `config/creators.yml`.
- SQLite schema for creators, raw posts, recipe extractions, and gold recipes.
- SQLite FTS5 gold recipe search index.
- Manual caption import through the web UI and CLI.
- Deterministic recipe extraction from pasted caption text.
- Creator sync command that detects new configured creators.
- Stubbed external-source ingestion interface with clear limitations.
- systemd service/timer templates for Ubuntu deployment.

## Not Built Yet

The following are intentionally not implemented yet:

- Authentication.
- AI extraction pipeline.
- nginx or Cloudflare integration for this project.
- Automated Instagram collection.

Do not treat the lack of automated Instagram collection as a bug. The working MVP path is manual caption import plus a clean ingestion interface for later approved API or creator-provided export workflows.

## Current Network Assumption

The Ubuntu server is the production host for this project. Local development and unit tests can run on the developer machine, but production data and scheduled jobs should happen on Ubuntu.

For the early direct-IP MVP, use TCP port `8000` for this project. Do not use ports already occupied by the existing CHS Finds/CHS Spots setup, especially `80`, `443`, `3000`, `3001`, or `3456`.

Until nginx or Cloudflare is intentionally configured for this project, the app should be reachable as:

```text
http://<server-ip>:8000/
```

The current preferred public URL uses the existing Cloudflare Tunnel:

```text
https://cocktails.chsfinds.com/
```

## How Future Agents Should Start

Future Codex sessions should begin by reading:

1. `AI_CONTEXT.md`
2. `instructions/PRODUCT_OWNER_NOTES.md`
3. `instructions/AI_BEHAVIOR.md`
4. `docs/ARCHITECTURE.md`
5. `tasks/NEXT_STEPS.md`

Before implementation, summarize the current assumptions and confirm only the choices that materially affect the build. Preserve the product goal, but challenge brittle implementation details when they would create real risk or unnecessary complexity.

For app work, run:

```bash
.venv/bin/pytest
.venv/bin/python -m app.cli sync-creators
```
