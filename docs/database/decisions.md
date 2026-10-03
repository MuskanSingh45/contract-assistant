# Database Decisions

## SQLite
Selected for the MVP because the prototype is local, single-user, and needs no database server.

## No ORM: `sqlite3` + SQL migrations
Raw SQL migrations are the single schema source. The backend uses the stdlib `sqlite3` with
small query functions in the services. This avoids keeping ORM models and SQL in sync
under time pressure. See [ADR 005](../decisions/005-schema-source-of-truth.md).

## Version-first model
Every analysis result hangs off a `contract_version`, so it stays tied to the exact
uploaded document.

## Citations as data
Citations are first-class rows linked to stored document segments. The model returns a
segment label and a quote. The backend verifies the quote and supplies page/section.

## Review history separate from confidence
The current `review_status` is on the item. The history is in the append-only `reviews`
table. `confidence` is never changed by a review.

## Renewals are calculated
Renewal facts are reviewed as extracted items. The `renewals` row is derived output. See
[ADR 006](../decisions/006-review-and-calculation-model.md).
