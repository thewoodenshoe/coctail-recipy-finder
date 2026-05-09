# Cocktail Recipe Finder

Cocktail Recipe Finder is an AI-first software project for building a searchable index of cocktail-related Instagram posts from selected cocktail creators.

The product owner should be able to provide creator handles and Instagram post links, then search the indexed content by terms like `gin`, `mezcal`, `negroni`, or `sour`. Search results should show the drink title when known, likely ingredients, extracted text, creator, and the original Instagram post link.

## MVP

The MVP should stay deliberately simple:

- Maintain a list of cocktail creators.
- Manually add an Instagram post URL.
- Paste the caption or visible post text.
- Extract likely recipe fields from the pasted text.
- Store the post, creator, extracted fields, and searchable text.
- Search across indexed posts using SQLite FTS5.
- View search results and post details in a basic web UI.

The default implementation direction is FastAPI, SQLite with FTS5, SQLAlchemy, Jinja templates, systemd, and nginx.

## Not Built Yet

This repo currently contains documentation and project instructions only.

The following are intentionally not implemented yet:

- Application scaffold.
- Python dependencies.
- Database schema or migrations.
- Frontend templates.
- Backend routes.
- Instagram scraping.
- Server deployment.
- Authentication.
- Background jobs.
- AI extraction pipeline.

Do not treat this absence as a gap to fill immediately. The first goal is to give future AI sessions enough context to build the MVP cleanly.

## How Future Agents Should Start

Future Codex sessions should begin by reading:

1. `AI_CONTEXT.md`
2. `instructions/PRODUCT_OWNER_NOTES.md`
3. `instructions/AI_BEHAVIOR.md`
4. `docs/ARCHITECTURE.md`
5. `tasks/NEXT_STEPS.md`

Before implementation, summarize the current assumptions and confirm only the choices that materially affect the build. Preserve the product goal, but challenge brittle implementation details when they would create real risk or unnecessary complexity.
