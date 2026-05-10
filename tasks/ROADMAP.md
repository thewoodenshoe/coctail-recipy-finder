# Roadmap

## Phase 0 - Repo And Docs

- Create AI-first project documentation.
- Capture product intent.
- Capture architecture direction.
- Capture security, deployment, and ingestion rules.
- Define next implementation steps.

## Phase 1 - App Scaffold

- Create Python project structure.
- Add FastAPI app.
- Add Jinja templates.
- Add local configuration loading.
- Add basic test setup.
- Add formatting/linting choices only as needed.

## Phase 2 - Manual Ingestion

- Add creator model.
- Add post model.
- Add import post form.
- Validate Instagram URLs.
- Store raw pasted caption text.
- Handle duplicate URLs.

## Phase 3 - Extraction And Search

- Add extracted recipe model.
- Implement initial deterministic extraction.
- Add SQLite FTS5 search index.
- Add search page and results.
- Add post detail page.
- Add tests for extraction and search.

## Phase 4 - Deployment

- Prepare Ubuntu deployment layout.
- Add systemd service documentation.
- Add nginx reverse proxy documentation.
- Configure environment variables.
- Deploy to direct IP if requested.
- Add basic hardening.

## Phase 5 - Improved Ingestion

- Evaluate workflow pain from manual ingestion.
- Consider official API or creator-authorized export options.
- Consider AI-assisted extraction if deterministic parsing is insufficient.
- Avoid non-approved automated collection behavior.
