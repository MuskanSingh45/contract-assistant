# API Documentation

This directory defines the contract between the frontend and the backend.

Start with [api-contract.md](api-contract.md). It has the conventions, the full endpoint
index and the shared objects.

| File | Covers |
|---|---|
| [api-contract.md](api-contract.md) | Conventions, endpoint index, shared objects and enums, health |
| [contracts.md](contracts.md) | Contract list, upload, details, extracted items |
| [analysis.md](analysis.md) | Starting and polling analysis, stages |
| [versions.md](versions.md) | Versions, new version upload, version comparison |
| [obligations.md](obligations.md) | Obligations list/detail, operational status |
| [renewals.md](renewals.md) | Calculated renewal and notice deadlines |
| [reviews.md](reviews.md) | Review queue, approve/edit/reject, history |
| [clarifications.md](clarifications.md) | Conflicts/ambiguities and their resolution |
| [citations.md](citations.md) | Source drawer content |
| [dashboard.md](dashboard.md) | Dashboard aggregate |
| [errors.md](errors.md) | Error shape and codes |

The frontend consumes these shapes and does not invent backend behaviour; its types are in
`frontend/src/lib/types.js` (JSDoc typedefs) and its test fixtures (`frontend/src/test/fixtures.js`) use the
same shapes. `db/seeds/development.sql` contains the same demo data as the examples.

The running backend serves its OpenAPI spec at http://localhost:8000/docs; it must match these docs.
Every response carries an `X-Request-ID` header ([errors.md](errors.md#request-ids)).
