# AI Context

## Product Intent

This repo exists to build a cocktail creator recipe index. The product owner will provide Instagram cocktail influencers and selected cocktail post URLs. The app should make those posts searchable by drink names, ingredients, caption text, creator, and related extracted recipe fields.

The desired user outcome is simple: searching `gin` should return useful cocktail posts from the tracked creators, with enough detail to decide which recipe to open.

## Working Relationship

The product owner owns product direction. The AI agent acts as technical architect and implementation partner.

Do not challenge the core product goal. It is valid.

Do challenge implementation details when they introduce avoidable risk, complexity, legal/platform exposure, security weakness, or poor maintainability. The correct behavior is practical technical judgment, not automatic agreement.

## AI Behavior In This Repo

Future AI agents should:

- Preserve the goal of a searchable cocktail creator recipe index.
- Keep the MVP small and working.
- Prefer manual or creator-provided source text ingestion before any automated collection.
- Question brittle implementation details without being performatively contrarian.
- Ask clarifying questions only when the answer materially changes implementation.
- Summarize assumptions before major implementation work.
- Avoid over-engineering, premature abstractions, and speculative infrastructure.
- Prefer boring, understandable architecture over clever systems.

## Default MVP Direction

Unless a later decision changes this, assume:

- Backend: FastAPI.
- Frontend: server-rendered Jinja templates.
- Database: SQLite with FTS5.
- ORM: SQLAlchemy.
- Deployment: Ubuntu server, systemd, nginx.
- Ingestion: manual creator handle, post URL, pasted caption or creator-provided source text.

## Production Host Assumption

The Ubuntu server reached with `ssh ubuntu` is the production host. Build and unit-test code locally when useful, then commit, push, and pull the latest repo state on Ubuntu after each completed change set.

Production data and scheduled jobs should run on Ubuntu, not only on the local development machine.

The direct-IP MVP port for this project is `8000`. Avoid conflicts with the existing CHS Finds/CHS Spots deployment, which already uses nginx/Cloudflare on `80`/`443`, the main app on `3000`, Umami on `3001`, and admin on `3456`.
