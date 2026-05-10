# Database

The active schema is a raw-to-gold pipeline. Legacy `posts`, `recipes`, and `search_index` tables are obsolete and are dropped by `init-db` if found.

## Active Tables

## `creators`

Tracked Instagram creators from `config/creators.yml`.

Key fields:

- `handle`
- `profile_url`
- `last_sync_at`
- `backfill_completed_at`
- `sync_status`
- `sync_error`
- `active`

## `raw_posts`

Source capture layer. Store original captured Instagram/source text and metadata as close to source as practical.

Key fields:

- `platform`
- `creator_id`
- `creator_handle_snapshot`
- `source_url`
- `external_post_id`
- `captured_at`
- `content_hash`
- `raw_json`
- `raw_caption_text`
- `raw_intro_text`
- `raw_hashtags_json`
- `raw_view_count`
- `raw_like_count`
- `raw_comment_count`
- `posted_at`
- `capture_completeness`
- `ingestion_provider`
- `ingestion_status`
- `ingestion_error`

## `recipe_extractions`

Transformation history. Each transformer run can create/update an extraction record for a raw post and transformer version.

Key fields:

- `raw_post_id`
- `transformer_name`
- `transformer_version`
- `status`
- `extracted_json`
- `confidence_score`
- `quality_score`
- `confidence_reasons_json`
- `created_at`
- `error`

## `gold_recipes`

Current best structured recipe records. Search and UI should read from this table, not raw text.

Key fields:

- `raw_post_id`
- `extraction_id`
- `creator_id`
- `creator_handle`
- `source_url`
- `drink_title`
- `drink_title_normalized`
- `intro_text`
- `base_spirits_json`
- `ingredients_json`
- `method`
- `garnish`
- `glassware`
- `tags_json`
- `confidence_score`
- `quality_score`
- `view_count`
- `like_count`
- `posted_at`
- `transformed_at`
- `transformer_version`
- `status`

## `gold_recipe_search_index`

SQLite FTS5 table for searchable gold recipes.

Indexed content:

- creator handle
- drink title
- normalized drink title
- base spirits
- ingredient names
- tags
- intro text
- raw fallback text

## Data Principles

- Preserve raw captured text.
- Treat extraction and gold records as rebuildable derived data.
- Store display values and normalized values where useful.
- Do not store media files.
- Do not store Instagram credentials or session state in the repo.
