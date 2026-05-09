# Next Steps

## Immediate Next Steps

1. Confirm whether the first application build should be local-only or deployment-ready from the beginning.
2. Decide whether MVP public access needs basic protection if deployed by direct IP.
3. Scaffold the FastAPI app without implementing scraping.
4. Create the initial SQLite schema and models.
5. Implement manual post ingestion.
6. Implement basic extraction and FTS5 search.
7. Add focused tests for URL validation, extraction, deduplication, and search.
8. After each completed change set, commit, push, and sync the Ubuntu server copy with `ssh ubuntu`, cloning under `projects` first if needed.

## Recommended Next Codex Prompt

Use this prompt for the next implementation step:

```text
Build Phase 1 of this repo: create the FastAPI app scaffold only.

Read AI_CONTEXT.md, instructions/*.md, docs/ARCHITECTURE.md, docs/BACKEND.md, docs/FRONTEND.md, docs/DATABASE.md, and tasks/ROADMAP.md first.

Do not implement Instagram scraping.
Do not deploy.
Do not connect to the Ubuntu server.

Create a minimal maintainable Python project structure for FastAPI + Jinja + SQLAlchemy + SQLite, add placeholder routes/templates only if useful, add basic config loading from environment variables, and add a test setup. Keep it boring and small. Before editing, summarize assumptions and any material tradeoffs.
```
