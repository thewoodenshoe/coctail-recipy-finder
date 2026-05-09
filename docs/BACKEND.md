# Backend

## Responsibilities

The backend should provide:

- Creator management.
- Post creation and deduplication.
- Caption storage.
- Recipe field extraction.
- Search indexing.
- Search result retrieval.
- Post detail retrieval.
- Basic validation and error handling.

## Proposed Routes

Initial server-rendered routes:

- `GET /` - search page.
- `GET /search?q=...` - search results.
- `GET /posts/new` - import post form.
- `POST /posts` - create post from form submission.
- `GET /posts/{post_id}` - post detail page.
- `GET /creators` - creator list.
- `GET /creators/{creator_id}` - creator detail and posts.

Optional JSON routes can be added later if needed, but they are not required for the first MVP.

## Service Boundaries

Keep backend logic separated into small services:

- Creator service: normalize handles and create or fetch creators.
- Post service: validate URLs, create posts, prevent duplicate URLs.
- Extraction service: parse pasted text into likely recipe fields.
- Search service: update and query FTS5 index.

Do not overbuild service layers. These boundaries are for clarity, not enterprise architecture.

## Validation

Validate:

- Creator handle is present.
- Instagram URL looks like an Instagram post or reel URL.
- Caption text is not empty.
- Duplicate post URLs are handled predictably.

Preserve the original user input where useful, but store normalized fields for search and deduplication.

## Error Handling

Errors should be understandable and recoverable:

- Duplicate URL: link to existing post.
- Invalid URL: ask for a valid Instagram post URL.
- Empty caption: ask for pasted text.
- Extraction failure: save raw post and mark extracted fields as empty or uncertain.
