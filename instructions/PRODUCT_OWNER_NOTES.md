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

Future agents may request temporary elevated access when needed for deployment work, package installation, firewall configuration, nginx, or systemd. Do not assume server access is available until the product owner explicitly asks for deployment work.

Never write elevated-access secrets into repo files, scripts, docs, commits, logs, `.env`, shell history, or issue text.

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

Ubuntu is the production server for this project. Local work is acceptable for coding and technical unit tests. Production data and scheduled jobs should run on Ubuntu.

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

- Non-approved automated collection.
- Hidden infrastructure complexity.
- Premature background worker systems.
- Unnecessary cloud services.
- Storing secrets or private account material in source control.
- Conflicting with CHS Finds/CHS Spots ports or nginx/Cloudflare settings.
