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

## Later Ingestion Options

Later options can include:

- Creator-authorized data access.
- Official APIs where practical.
- Browser-assisted import.
- Limited public metadata import.
- Semi-manual tools that reduce copy/paste.

## Explicit Non-Goals

- Do not download videos.
- Do not mirror Instagram profiles.
- Do not build login bypass.
- Do not build CAPTCHA bypass.
- Do not build rate-limit evasion.
- Do not build aggressive scraping behavior.
