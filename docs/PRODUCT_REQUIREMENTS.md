# Product Requirements

## Product Summary

Build a searchable index of cocktail-related Instagram posts from selected cocktail creators.

The product owner should be able to add creators, add posts, paste caption text, extract recipe-like fields, and search the resulting index.

## User Stories

- As the product owner, I can add a cocktail creator by Instagram handle so their posts can be grouped.
- As the product owner, I can add an Instagram post URL for a creator so the original source is preserved.
- As the product owner, I can paste a caption or visible post text so the app can index source material that I provide.
- As the product owner, I can see likely drink title, ingredients, instructions, and extracted text so the recipe is easier to browse.
- As the product owner, I can search for an ingredient or drink term so I can find relevant posts quickly.
- As the product owner, I can open the original Instagram link from a result so I can inspect the source post.
- As the product owner, I can view all posts for a creator so I can audit coverage.

## MVP Acceptance Criteria

- A creator can be created with a normalized handle.
- A post can be created with creator, Instagram URL, pasted caption text, and optional notes.
- The system preserves the original pasted text.
- The system extracts likely recipe fields from pasted text.
- Search returns relevant posts for ingredient and drink-name queries.
- Search results show creator, title when available, likely ingredients, text excerpt, and original link.
- A post detail page shows raw text and extracted fields.
- Duplicate post URLs are prevented or clearly handled.
- The app runs locally with a SQLite database.

## Non-Goals

- Automated Instagram collection.
- Video downloading.
- Login or user account system.
- Multi-user permissions.
- Mobile app.
- Complex AI pipeline.
- External search service.
- Cloud deployment.
- Perfect recipe extraction.
- Full Instagram profile mirroring.
