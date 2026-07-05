# Ingestion Rules

## Risk Area

Instagram source ingestion is a risk area. Reliability, platform rules, account safety, and maintenance cost matter.

Do not build unattended automated collection as the default ingestion model.

## MVP Ingestion

The first MVP should allow:

1. Enter creator handle.
2. Enter Instagram post URL.
3. Paste caption or visible post text.
4. Extract likely recipe fields from the pasted text.
5. Index searchable text.

This validates the core product: searchable cocktail recipe discovery.

## Later Options

Later ingestion options can include:

- Creator-authorized access.
- Official APIs where practical.
- Limited public metadata import.
- Semi-manual workflows that reduce copy/paste without working around platform controls.
- Owner-authorized manual Chrome sessions for occasional backfills, when the
  owner is logged in locally and has permission to view the source content.

## Boundaries

Do not download videos.

Do not build unattended or scheduled browser scraping.

Do not store account sessions, secrets, passwords, private account material, or
systems designed to work around platform controls.

Manual Chrome ingestion is approved when all of these are true:

- The run is initiated by the owner in this workspace.
- The browser session is the owner's existing local Chrome session.
- The collector captures only post URL and visible caption/source text needed
  for this recipe index.
- The run stops once it reaches already-indexed posts.
- The output is imported through the existing JSONL/raw-post/gold pipeline.
- No persistent browser credential, session cookie, or background collection
  service is added to the repo.

If automated ingestion is proposed later, evaluate it against reliability, compliance, maintenance cost, and product value before implementation.
