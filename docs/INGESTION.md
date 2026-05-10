# Ingestion

## MVP Flow

The first ingestion flow is manual by design:

1. User enters creator handle.
2. User enters Instagram post URL.
3. User pastes caption or visible post text.
4. App extracts likely recipe fields.
5. App indexes searchable text.

This is the simplest practical path. It validates the product without taking on scraping fragility first.

## Extraction

Initial extraction should focus on likely fields:

- Drink title.
- Ingredients.
- Instructions or method.
- Garnish.
- Glassware.

The app should preserve raw caption text even when extraction is poor.

Extraction can start with deterministic parsing. AI-assisted extraction can be added later if examples show deterministic parsing is too weak.

## Search Indexing

Index:

- Creator handle.
- Drink title.
- Ingredients.
- Instructions.
- Raw caption text.
- Notes.

Search should return the original Instagram URL with every result.

## Browser-Assisted Instagram Text Ingestion

The production ingestion path may use an authorized Playwright browser session on Ubuntu.

- Store session state outside the repo at `INSTAGRAM_SESSION_STATE_PATH`.
- Do not store Instagram credentials in the repo or in documentation.
- Do not download videos or media; block image, media, and font resources where practical.
- Store fetched visible post text as raw source material before parsing.
- Treat recipe extraction and search indexing as derived data that can be rebuilt locally.

Backfill discovers visible `/p/...` and `/reel/...` URLs from each configured profile and fetches text for each post. Incremental sync checks a smaller recent window and stops after enough known posts are seen.

Operational finding from the first full Ubuntu backfill attempt:

- Profile discovery can find post URLs while individual post pages still render empty or as Instagram error pages in headless Chromium.
- Do not treat discovered URLs as captured content.
- Do not store Instagram error pages such as `Sorry, this page isn't available` as raw posts.
- If a full run returns mostly `No caption text extracted`, stop and inspect the authorized browser session before retrying a large backfill.
- A reliable large backfill likely needs a refreshed authorized browser session, an operator-assisted browser mode, or another creator-authorized/API path.

## Later Ingestion Options

Later options can include:

- Creator-authorized data access.
- Official APIs where practical.
- Browser-assisted import.
- Limited public metadata import.
- Semi-manual tools that reduce copy/paste.

## Current Implementation

The current working ingestion path is manual caption import.

Available commands:

```bash
python -m app.cli sync-creators
python -m app.cli import-caption --creator HANDLE --url URL --caption-file FILE
```

`sync-creators` reads `config/creators.yml`, upserts creators into the database, detects newly configured creators, and chooses backfill or incremental sync.

Unauthenticated public Instagram scraping is intentionally not implemented. `app/ingestion/instagram_public.py` is a stubbed provider that records a clear status message instead of depending on brittle or abusive scraping. Use `--provider instagram-browser` after creating an authorized browser session.

## Explicit Non-Goals

- Do not download videos.
- Do not mirror Instagram profiles.
- Do not build login bypass.
- Do not build CAPTCHA bypass.
- Do not build rate-limit evasion.
- Do not build aggressive scraping behavior.
