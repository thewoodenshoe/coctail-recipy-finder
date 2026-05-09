# Deployment

## Target Environment

The intended deployment target is an Ubuntu server.

Server access may eventually be available through:

```bash
ssh ubuntu
```

The product owner has approved using this server as the production host for this project. Future agents should still avoid changing nginx, Cloudflare, firewall, or systemd unless the current task requires it.

## MVP Deployment Shape

Likely deployment:

- FastAPI app running with Uvicorn.
- systemd service keeps the app running.
- nginx reverse proxy handles public HTTP traffic.
- SQLite database stored on the server filesystem.
- Environment variables configure host, port, app environment, and database path.

Deployment templates live in `deploy/`:

- `deploy/cocktail-index.service`
- `deploy/cocktail-index-sync.service`
- `deploy/cocktail-index-sync.timer`
- `deploy/README.md`

Ubuntu may need the venv package before `.venv` can be created:

```bash
sudo apt-get install -y python3.12-venv
```

## Direct IP Access

Direct IP access is acceptable for MVP.

See `docs/NETWORK_TROUBLESHOOTING.md` before changing ports, firewall rules, nginx, or Google Home forwarding.

The direct-IP MVP should use this project's reserved TCP port:

```text
8000
```

Expected URL shape:

```text
http://<server-ip>:8000/
```

Current smoke-test page:

```text
http://<server-ip>:8000/hello_world.html
```

A compatibility alias also exists at:

```text
http://<server-ip>:8000/hell_world.html
```

Current Ubuntu LAN IP observed during setup:

```text
192.168.86.250
```

For internet access from outside the LAN, configure Google Home / router port forwarding:

```text
External TCP 8000 -> 192.168.86.250 TCP 8000
```

Current Ubuntu firewall state for this project:

```bash
sudo ufw allow 8000/tcp
```

Rollback if the direct-port MVP is removed:

```bash
sudo ufw delete allow 8000/tcp
```

Recommended shape for the direct-port MVP:

- App binds to `0.0.0.0` on port `8000`.
- nginx remains untouched.
- Cloudflare remains untouched.
- Firewall allows SSH and TCP `8000`.
- Database file is not stored under a public web root.

When this project later moves behind nginx, bind the app to `127.0.0.1` and proxy from nginx. Do not do that yet unless explicitly requested.

## Existing CHS Finds / CHS Spots Deployment

The sibling CHS Finds / CHS Spots setup already uses:

- nginx and Cloudflare-facing traffic on `80` and `443`.
- Main Next.js app on `3000`.
- Umami on `3001`.
- Admin service on `3456`.
- nginx also listens on `8080`; do not use `8080` for this project.
- Additional occupied ports observed on the Ubuntu host: `3030`, `8080`, `8096`.

Do not reuse those ports for this project.

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

## Local Vs Ubuntu Work

Use local development for coding and unit tests.

Use Ubuntu for:

- Production serving.
- Production database files.
- Real ingestion runs.
- Any future Instagram-related collection work.

This avoids confusing local test data with production data and keeps the deployed state reproducible from git.
