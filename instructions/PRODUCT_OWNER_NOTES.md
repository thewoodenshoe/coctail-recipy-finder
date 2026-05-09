# Product Owner Notes

## Durable Instructions

The product goal is to build a searchable index of cocktail-related Instagram posts from selected cocktail creators.

The product owner wants direct, practical technical guidance. Do not validate weak technical assumptions automatically. If a proposed implementation creates a real problem, say so plainly and recommend the simplest practical path.

The app should start simple. Optimize for a working MVP before adding automation, complex infrastructure, or broad ingestion systems.

## Server Access

Ubuntu server access may eventually be available through:

```bash
ssh ubuntu
```

Future agents may request `sudo` when needed for deployment work, package installation, firewall configuration, nginx, or systemd. Do not assume server access is available until the product owner explicitly asks for deployment work.

If sudo is needed, ask the product owner for a temporary sudo password directly and keep moving once provided. Use wording like:

```text
I need sudo. Give me the temporary password, and update it once we are done.
```

Never write sudo passwords into repo files, scripts, docs, commits, logs, `.env`, shell history, or issue text.

After each completed change set, the expected workflow is to commit, push, then sync the Ubuntu server copy:

```bash
git commit
git push
ssh ubuntu
cd projects
git pull
```

For the initial server setup, clone the repo under `projects` if it is not already present.

This rule should be applied to coherent completed changes after verification, not to every individual file save.

Ubuntu is the production server for this project. Local work is acceptable for coding and technical unit tests. Production data, real ingestion runs, and any future Instagram-related collection work should run on Ubuntu.

## Secrets

Secrets must never be stored in the repo.

Use environment variables for configuration. Keep `.env.example` limited to placeholders and safe defaults.

## Implementation Bias

Prefer:

- Manual ingestion first.
- SQLite before external database services.
- Server-rendered pages before a separate frontend app.
- Clear data model before automation.
- Tests around parsing, extraction, and search behavior.
- Direct-IP MVP serving on this project's reserved port `8000` before nginx/Cloudflare integration.

Avoid:

- Aggressive scraping.
- Hidden infrastructure complexity.
- Premature background worker systems.
- Unnecessary cloud services.
- Storing credentials, tokens, cookies, or session data in source control.
- Conflicting with CHS Finds/CHS Spots ports or nginx/Cloudflare settings.
