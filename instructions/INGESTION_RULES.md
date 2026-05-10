# Ingestion Rules

## Risk Area

Instagram source ingestion is a risk area. Reliability, platform rules, account safety, and maintenance cost matter.

Do not start by building automated collection.

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

## Boundaries

Do not download videos.

Do not build non-approved automated collection behavior.

Do not store account sessions, secrets, private account material, or systems designed to work around platform controls.

If automated ingestion is proposed later, evaluate it against reliability, compliance, maintenance cost, and product value before implementation.
