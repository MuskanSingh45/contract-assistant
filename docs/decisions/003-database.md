# ADR 003 — Database

## Decision
Use SQLite for MVP.

## Reason
Simple local deployment and no production multi-user database requirement for the initial submission.

Persistence logic should remain separated from domain logic to allow a future database change.
