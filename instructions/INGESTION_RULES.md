# Ingestion Rules

## Risk Area

Instagram ingestion is a risk area. Reliability, platform rules, account safety, and maintenance cost matter.

Do not start by building a scraper.

## MVP Ingestion

The first MVP should allow:

1. Enter creator handle.
2. Enter Instagram post URL.
3. Paste caption or visible post text.
4. Extract likely recipe fields from the pasted text.
5. Index searchable text.

This avoids brittle scraping and still validates the core product: searchable cocktail recipe discovery.

## Later Options

Later ingestion options can include:

- Creator-authorized access.
- Official APIs where practical.
- Browser-assisted import.
- Limited public metadata import.
- Semi-manual workflows that reduce copy/paste without bypassing controls.

## Boundaries

Do not download videos.

Do not build abusive scraping behavior.

Do not build login bypass, CAPTCHA bypass, rate-limit evasion, credential farming, or systems designed to avoid platform controls.

If automated ingestion is proposed later, evaluate it against reliability, compliance, maintenance cost, and product value before implementation.
