# Next Steps

## Immediate Next Steps

1. Confirm whether the first application build should be local-only or deployment-ready from the beginning.
2. Decide whether MVP public access needs basic protection if deployed by direct IP.
3. Verify the direct static smoke page on Ubuntu port `8000`.
4. Scaffold the FastAPI app without implementing automated Instagram collection.
5. Create the initial SQLite schema and models.
6. Implement manual post ingestion.
7. Implement basic extraction and FTS5 search.
8. Add focused tests for URL validation, extraction, deduplication, and search.
9. After each completed change set, commit, push, and sync the Ubuntu server copy with `ssh ubuntu`, cloning under `projects` first if needed.

## Recommended Next Codex Prompt

Use this prompt for the next implementation step:

```text
Build Phase 1 of this repo: create the FastAPI app scaffold only.

Read AI_CONTEXT.md, instructions/*.md, docs/ARCHITECTURE.md, docs/BACKEND.md, docs/FRONTEND.md, docs/DATABASE.md, and tasks/ROADMAP.md first.

Do not implement automated Instagram collection.
Do not deploy.
Do not configure nginx, Cloudflare, systemd, or firewall unless explicitly requested.

Create a minimal maintainable Python project structure for FastAPI + Jinja + SQLAlchemy + SQLite, add placeholder routes/templates only if useful, add basic config loading from environment variables, and add a test setup. Keep it boring and small. Before editing, summarize assumptions and any material tradeoffs.

After verification, commit, push, then run `ssh ubuntu`, `cd ~/projects/coctail-recipy-finder`, and `git pull --ff-only`.
```
