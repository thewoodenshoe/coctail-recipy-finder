# Deployment

## Target Environment

The intended deployment target is an Ubuntu server.

Server access may eventually be available through:

```bash
ssh ubuntu
```

Do not connect to the server until deployment work is explicitly requested.

## MVP Deployment Shape

Likely deployment:

- FastAPI app running with Uvicorn.
- systemd service keeps the app running.
- nginx reverse proxy handles public HTTP traffic.
- SQLite database stored on the server filesystem.
- Environment variables configure host, port, app environment, and database path.

## Direct IP Access

Direct IP access is acceptable for MVP.

Recommended shape:

- nginx listens on port 80.
- FastAPI app binds to `127.0.0.1`.
- Firewall allows SSH and HTTP.
- Database file is not stored under a public web root.

## Future Domain And HTTPS

If the app becomes more than a private MVP, add:

- Domain name.
- HTTPS with Let's Encrypt or equivalent.
- Stronger access controls if sensitive data is added.

Do not block MVP deployment on domain setup unless the product owner requires it.

## Before Applying Server Changes

Before changing nginx, firewall, or systemd, document:

- Exact file paths.
- Commands to run.
- Purpose of the change.
- Rollback path.

This matters because deployment mistakes on a public IP can expose the app or lock out access.

## Repo Sync Workflow

After a completed change set is verified locally:

1. Commit the changes.
2. Push to the configured git remote.
3. Run `ssh ubuntu`.
4. Run `cd projects`.
5. If this is the first sync and the repo is missing, clone it.
6. Otherwise, enter the repo and run `git pull`.

This keeps the server copy current without treating incomplete local edits as deployable states.
