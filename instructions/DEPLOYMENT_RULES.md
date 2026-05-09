# Deployment Rules

## Target

The eventual target is an Ubuntu server.

The likely MVP deployment shape is:

- FastAPI application.
- SQLite database on local disk.
- systemd service.
- nginx reverse proxy.
- Direct IP access at first.

## Direct IP MVP

Direct IP access is acceptable for the MVP. That does not mean the server should be wide open.

Reasonable MVP hardening includes:

- App bound to `127.0.0.1` when behind nginx.
- nginx exposed on HTTP.
- Firewall allowing only needed ports.
- Clear file ownership for app and database files.
- No secrets committed to git.

## Documentation Before Changes

Before applying firewall, nginx, or systemd changes, document:

- What file will change.
- What command will be run.
- Why it is needed.
- How to roll it back.

Do not connect to the Ubuntu server unless the product owner asks for deployment work.

## Git And Server Sync Workflow

After each completed change set, future agents should:

1. Run relevant verification.
2. Commit the change to git with a clear message.
3. Push the commit to the configured remote.
4. Connect to the Ubuntu server with `ssh ubuntu`.
5. Change into the server projects directory.
6. Pull the latest version of this repo.

Do this after completed, coherent changes, not after every individual file edit. Shipping half-finished edits to the server is a bad operational habit.

For the first server sync, if the repo does not exist under the server projects directory, clone it from the configured git remote instead of running `git pull`.

## Future HTTPS

A domain and HTTPS should be added later if the app becomes more than a private MVP. Do not block the first deployment on domain setup unless the product owner requires it.
