# Database

## Recommendation

Use SQLite for the MVP with SQLAlchemy models and SQLite FTS5 for full-text search.

SQLite is enough for a single-owner internal tool and keeps deployment simple.

## Proposed Tables

The current implementation uses SQLAlchemy models in `app/models.py` and an app-managed SQLite FTS5 table created by `app/db.py`.

## `creators`

Stores tracked Instagram creators.

Suggested columns:

- `id`
- `handle`
- `display_name`
- `profile_url`
- `notes`
- `created_at`
- `updated_at`

Constraints:

- Unique normalized `handle`.

## `posts`

Stores source post records.

Suggested columns:

- `id`
- `creator_id`
- `instagram_url`
- `normalized_url`
- `caption_text`
- `source_type`
- `notes`
- `created_at`
- `updated_at`

Constraints:

- Unique `normalized_url`.
- Foreign key to `creators`.

## `extracted_recipes`

Stores extracted recipe-like fields for a post.

Suggested columns:

- `id`
- `post_id`
- `drink_title`
- `ingredients_text`
- `instructions_text`
- `garnish_text`
- `glassware`
- `confidence`
- `extraction_method`
- `created_at`
- `updated_at`

Constraints:

- One current extracted recipe per post for MVP, unless later examples require multiple recipes per post.

## `search_index`

Use SQLite FTS5 if needed as a virtual table.

Suggested indexed content:

- Creator handle.
- Drink title.
- Ingredients.
- Instructions.
- Caption text.
- Notes.

Implementation options:

- FTS5 virtual table maintained by app code after post create/update.
- FTS5 external-content table tied to `posts` if the schema benefits from it later.

For MVP, app-managed updates are simpler and easier to reason about.

## Data Principles

- Preserve raw caption text.
- Store extracted fields separately.
- Store normalized URLs for deduplication.
- Do not store media files.
- Do not store Instagram login/session credentials.
