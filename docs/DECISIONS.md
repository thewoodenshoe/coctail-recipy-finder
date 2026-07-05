# Decisions

This file is the architectural decision log. Add new decisions as the project evolves.

## 0001 - Use Manual Caption Ingestion First

Status: Accepted

Decision: The first MVP will allow manual ingestion by creator handle, Instagram post URL, and pasted caption text.

Reasoning: Manual ingestion validates the core product without taking on platform compliance issues, account risk, or brittle automation too early.

Consequences:

- Data entry is slower at first.
- The MVP can be built and tested faster.
- The system preserves source URLs and raw text.
- Later ingestion improvements can be added after the index/search workflow proves useful.

## 0002 - Use FastAPI, SQLite FTS5, SQLAlchemy, Jinja, systemd, and nginx

Status: Accepted

Decision: The default MVP stack is FastAPI, SQLite with FTS5, SQLAlchemy, Jinja templates, systemd, and nginx.

Reasoning: The product is a small internal CRUD/search app. This stack minimizes moving parts while leaving room for clean growth.

Consequences:

- Deployment is straightforward on Ubuntu.
- Search can be implemented without an external search service.
- A separate frontend app is unnecessary for MVP.
- SQLite may need to be replaced later if concurrency, multi-user access, or data size grows significantly.

## 0003 - Use Direct Port 8000 Before nginx or Cloudflare

Status: Accepted

Decision: The first live smoke-test and early MVP serving path will use direct HTTP access on TCP port `8000`.

Reasoning: The existing CHS Finds / CHS Spots deployment already uses nginx, Cloudflare, `80`, `443`, `3000`, `3001`, and `3456`. A separate direct port avoids conflicts while this project is still early.

Consequences:

- Google Home / router forwarding must map external TCP `8000` to the Ubuntu server's TCP `8000`.
- The app must bind to `0.0.0.0:8000` for direct LAN/public testing.
- This is not the final hardened deployment shape.
- nginx/Cloudflare integration can be added later when there is a real app worth fronting.

## 0004 - Ubuntu Is The Production Data Host

Status: Accepted

Decision: Local development is acceptable for coding and unit tests, but production data, ingestion runs, and future Instagram-related collection work should run on Ubuntu.

Reasoning: Keeping production data on the production server avoids drift between local experiments and deployed behavior.

Consequences:

- Future agents should commit, push, and pull on Ubuntu after each completed change set.
- Local test data should be treated as disposable.
- Any real ingestion job must be designed to run safely on Ubuntu.

## 0005 - Stub Public Instagram Provider Until Approved Import Path Exists

Status: Accepted

Decision: The initial app ships with a manual ingestion provider and a stubbed public Instagram provider.

Reasoning: Automated public Instagram collection is brittle and platform-sensitive. The MVP should validate creator registry, manual import, extraction, indexing, search, and deployment before taking on ingestion risk.

Consequences:

- `sync-creators` records backfill/incremental status but does not fetch Instagram posts yet.
- Manual import is the working content path.
- Future API or creator-provided import can be added behind the existing ingestion interface.

## 0008 - Remove Browser-Based Collection From Active Code

Status: Superseded by 0009

Decision: Remove the active browser-based ingestion commands, provider, related configuration, automation dependency, and related deployment instructions.

Reasoning: The product is a searchable recipe index that links back to original Instagram posts. Active browser-based collection is a platform-sensitive implementation detail and creates unnecessary compliance and security review risk for the MVP.

Consequences:

- Manual caption/source-text import remains the supported working ingestion path.
- `sync-creators` can still track configured creators and status through the stub provider.
- Future ingestion must use an approved API, creator-provided export, or another explicitly reviewed data source.

## 0009 - Allow Owner-Initiated Manual Chrome Backfills

Status: Accepted

Decision: Allow occasional owner-initiated manual Chrome backfills using the
owner's existing local authenticated Chrome session.

Reasoning: The product owner has permission to view the selected creators'
content and wants infrequent manual refreshes, not a background scraper. This
keeps ingestion practical while avoiding stored credentials, unattended browser
automation, or daemonized collection.

Consequences:

- Manual Chrome runs may capture post URL and visible caption/source text.
- Collection stops when already-indexed posts are reached.
- Captured rows are imported through the existing JSONL/raw-post/gold pipeline.
- The repo must not store Chrome cookies, passwords, account sessions, or private
  session material.
- Scheduled sync remains conservative and should not use browser sessions.

## 0006 - Keep Direct-Port MVP On 8000, Not 8080

Status: Accepted

Decision: Keep this project's direct-port MVP on TCP `8000`.

Reasoning: CHS Finds / CHS Spots already has nginx listening on `8080`, and its Cloudflare firewall script explicitly removes broad public `8080` rules. Reusing `8080` would collide with existing host behavior.

Consequences:

- Google Home/router forwarding must use external TCP `8000` to internal `192.168.86.250:8000`.
- If public `8000` fails while LAN `8000` works, troubleshoot router/NAT/upstream behavior before changing app ports.
- Longer term, Cloudflare Tunnel or nginx/Cloudflare is the more robust public exposure path.

## 0007 - Expose MVP Through Existing Cloudflare Tunnel

Status: Accepted

Decision: Expose this app at `https://cocktails.chsfinds.com/` through the existing `chsfinds` Cloudflare Tunnel, routing to `http://localhost:8000` on Ubuntu.

Reasoning: The ISP/router path appears unreliable for direct inbound forwarding. CHS Finds already solved this class of problem with Cloudflare Tunnel, which uses outbound connectivity from Ubuntu and does not require public inbound port forwarding.

Consequences:

- The direct LAN URL remains `http://192.168.86.250:8000/`.
- The preferred public URL is `https://cocktails.chsfinds.com/`.
- The tunnel config in `/etc/cloudflared/config.yml` is now shared by CHS Finds and this app, so future edits must preserve both hostnames.
