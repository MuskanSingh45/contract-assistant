# Frontend Architecture

React 18 + JavaScript (JSX) + Vite + Tailwind 3 + React Router, built in-repo from the product designs ([ADR 008](../decisions/008-frontend-language.md)). The API client is `src/lib/api.js`; the API data shapes are documented as JSDoc typedefs in `src/lib/types.js`.

## Routes

| Route | Page | Data |
|---|---|---|
| `/` | redirect → `/dashboard` | |
| `/dashboard` | Dashboard | `GET /api/dashboard` |
| `/contracts` | Contract list | `GET /api/contracts` |
| `/contracts/upload` | Upload | `POST /api/contracts` → `POST /api/contracts/{id}/analyze` |
| `/contracts/:id/analyzing` | Analysis progress | poll `GET /api/contracts/{id}/analysis` every 2 s |
| `/contracts/:id` | Contract details (tabs) | see [pages.md](pages.md) |
| `/obligations` | Cross-contract obligations | `GET /api/obligations` |
| `/renewals` | Renewals and notice deadlines | `GET /api/renewals` |
| `/review` | Review queue and clarifications | `GET /api/reviews/queue`, `GET /api/clarifications?status=open`, `GET /api/reviews/recent` |
| `/review/:entityType/:entityId` | Single-item review (original vs edited value, source) | `GET /api/items/{type}/{id}`, `GET /api/citations/{id}` |
| `/settings`, `/help` | API/model health; about and disclaimer | `GET /api/health` |

The analysis route includes `:id` (the old route was `/contracts/analyzing`), so the page
knows which contract to poll and survives a refresh.

Contract details tabs: Overview, Extracted Information, Obligations, Versions. The active
tab is kept in the query string (`?tab=obligations`).

## API layer
- `src/lib/api.js` is the only module that calls the backend. It wraps `fetch` with `VITE_API_BASE_URL` (default `http://localhost:8000/api`) and has one function per endpoint in `docs/api/`. Data shapes are JSDoc typedefs in `src/lib/types.js`.
- There is no mock mode. Tests stub `api.*` functions or `fetch` instead (see Testing).
- `src/lib/useApi.js` loads data for a page: `{data, error, loading, reload}`. It ignores responses that arrive after the inputs changed.

## Error handling
Every failure reaches the UI as an `ApiError {code, message, status, details, requestId}`:

| Source | `code` | Shown as |
|---|---|---|
| Backend error body ([errors.md](../api/errors.md)) | the backend code, e.g. `CONTRACT_NOT_FOUND` | its `message` |
| Backend unreachable (`fetch` rejected) | `NETWORK_ERROR` | "Cannot reach the server. Is the backend running?" |
| No response within 30 s (uploads: 120 s) | `TIMEOUT` | "The server took too long to respond." |
| Non-JSON error (e.g. a proxy 502) | `INTERNAL_ERROR` (5xx) / `REQUEST_FAILED` | "Request failed (status)" |

- **Page loads** go through `Async` / `ErrorState` (`components/ui/States.jsx`): a title by code, the message, the server **Reference** (request ID) when there is one, and **Try again**. If a reload fails while data is already on screen, the data stays.
- **Validation** happens before anything is sent: upload checks type and size; the edit and answer forms use `validateEditValue()` (`components/review/validation.js`), which follows the value schemas in `ai/schemas/` and the backend. Messages appear under the field (with `aria-invalid`/`aria-describedby`) once it has been touched or Save was clicked; Save shows every problem and does not call the API until they are fixed. The backend still validates and its `VALIDATION_ERROR` is shown inline.
- **Actions** (approve, resolve, upload) show the message inline in the form or dialog that failed, or as an error toast. The dialog stays open so nothing typed is lost. `errorMessage(e)` is the one way to turn a thrown value into text.
- **Render crashes** are caught per page by `components/ErrorBoundary.jsx` (inside `AppShell`, keyed by route), so the navigation keeps working and moving to another page recovers.
- **Console logging:** 4xx are `console.warn`, 5xx and crashes are `console.error`, each with the request ID. The request ID is the same one the backend writes to its log ([backend logging](../architecture/backend-architecture.md#logging)).

## Testing
Vitest + Testing Library + jsdom; run `npm test` in `frontend/` or `make test`. Tests sit next to the code (`*.test.js(x)`); helpers are in `src/test/` (`renderWithApp` renders with the router, toast and source-drawer providers; `fixtures.js` builds objects in the `docs/api/` shapes). See [testing strategy](../testing/strategy.md#frontend).

## Rules
- The frontend displays backend state. It never calculates deadlines, `days_until`, lifecycle status or review transitions; it only formats dates.
- After a review or clarification action, use the returned `item`/`renewal` (or refetch). Do not patch derived values locally.
- Empty states must say what is missing ("Not found in document" vs "Analysis not run yet").
