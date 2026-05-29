# Ingestion

## MVP Flow

The first ingestion flow is manual by design:

1. User enters creator handle.
2. User enters Instagram post URL.
3. User pastes caption or visible post text.
4. App extracts likely recipe fields.
5. App indexes searchable text.

This is the simplest practical path. It validates the product without taking on platform-sensitive collection work first.

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

## Approved Source Text Ingestion

The active production path is manual or creator-provided text import. The app stores source text and links, then transforms that source material into searchable recipe records.

Any future automated provider must be reviewed before implementation and must use an approved API, creator-provided export, or another clearly permitted data source. Do not add browser-session capture or platform-control workarounds to this repo.

## Later Ingestion Options

Later options can include:

- Creator-authorized data access.
- Official APIs where practical.
- Limited public metadata import.
- Semi-manual tools that reduce copy/paste.

## Current Implementation

The current working ingestion path is captured creator-provided JSONL import. Each JSONL row should contain at least a source URL and caption text. Rows are imported into `raw_posts`, transformed into extraction records, and promoted into the searchable gold index.

Available commands:

```bash
python -m app.cli sync-creators
python -m app.cli import-jsonl --creator HANDLE --jsonl-file FILE --replace-creator-data
```

`sync-creators` reads `config/creators.yml`, upserts creators into the database, detects newly configured creators, and chooses backfill or incremental sync.

Unauthenticated public Instagram collection remains conservative. Bulk imports should use approved creator-provided or otherwise authorized captured source text.

## Explicit Non-Goals

- Do not download videos.
- Do not mirror Instagram profiles.
- Do not automate around platform access controls.
- Do not store account sessions, secrets, or private account material in this repo.
- Do not add non-approved collection behavior.
