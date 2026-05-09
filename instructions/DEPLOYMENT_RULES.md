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

For the early MVP, this project should use TCP port `8000` directly:

```text
http://<server-ip>:8000/
```

Do not configure this project on nginx, Cloudflare, ports `80`/`443`, or the existing CHS Finds/CHS Spots ports unless the product owner explicitly asks for that later.

Known ports to avoid on the Ubuntu host:

- `80` and `443`: nginx / Cloudflare-facing CHS Finds entrypoints.
- `3000`: CHS Spots main app.
- `3001`: Umami.
- `3456`: CHS Spots admin.
- `8080`: nginx / CHS-related listener; do not reuse for this project.
- `3030`, `8096`: already occupied on the host.

Reasonable MVP hardening includes:

- App bound to `127.0.0.1` when behind nginx.
- App bound to `0.0.0.0` only when intentionally testing direct `ip:8000` access.
- Firewall allowing only needed ports, currently SSH and TCP `8000` for the direct-port MVP.
- Clear file ownership for app and database files.
- No secrets committed to git.

If public IP access fails while LAN access works, consult `docs/NETWORK_TROUBLESHOOTING.md` before changing server config.

## Documentation Before Changes

Before applying firewall, nginx, or systemd changes, document:

- What file will change.
- What command will be run.
- Why it is needed.
- How to roll it back.

The product owner has approved Ubuntu sync for this project. Do not make server configuration changes unless the current task requires them.

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

## Sudo Handling

If sudo is required, ask the product owner for a temporary sudo password and continue after it is provided. Never store the password in the repo or write it into documentation.

Use sudo only for operations that actually need it, such as firewall, nginx, systemd, package installation, or privileged file ownership changes.

## Future HTTPS

A domain and HTTPS should be added later if the app becomes more than a private MVP. Do not block the first deployment on domain setup unless the product owner requires it.
