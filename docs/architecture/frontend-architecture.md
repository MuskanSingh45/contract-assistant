# Frontend Architecture

Summary only. The detailed docs are in [docs/frontend/](../frontend/architecture.md).

- React 18 + JavaScript (JSX) + Vite + Tailwind 3 + React Router, built in this repo from the product designs ([ADR 008](../decisions/008-frontend-language.md)).
- Displays backend state. It never calculates dates or review transitions.
- One API module (`src/lib/api.js`); every failure becomes an `ApiError` with the backend request ID. A per-page error boundary keeps navigation working after a crash. Details: [frontend error handling](../frontend/architecture.md#error-handling).
- Tested with Vitest + Testing Library ([testing strategy](../testing/strategy.md#frontend)).
