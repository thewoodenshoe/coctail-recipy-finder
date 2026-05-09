# Coding Standards

## General Principles

Prefer boring, maintainable code. The MVP should be easy to inspect, test, and modify.

Use the patterns already present in the repo once application code exists. Do not introduce a new framework, architecture style, or dependency without a practical reason.

## Code Organization

- Keep files small.
- Keep modules focused on one responsibility.
- Use clear names over clever names.
- Prefer explicit data flow.
- Avoid premature abstractions.
- Avoid large utility modules that become dumping grounds.

## Testing

Add tests for behavior that can silently corrupt the product value:

- Caption parsing.
- Recipe field extraction.
- Search indexing.
- Search ranking or filtering.
- URL validation.
- Creator/post deduplication.

Do not chase exhaustive test coverage before the MVP exists. Focus on logic where regressions would be hard to spot manually.

## Data Handling

- Normalize creator handles consistently.
- Preserve original pasted text.
- Store extracted fields separately from raw text.
- Prefer deterministic parsing first; introduce AI extraction only when it is clearly useful.
- Keep extraction output inspectable and editable.

## Dependencies

Dependencies should earn their place. Prefer the Python standard library and established framework features when they are enough.
