# ADR 008 — Frontend Language and Ownership

## Status
Accepted (2026-10-03).

## Update (2026-10-03)
Lovable was dropped because of the deadline. The frontend is built in this repo from the product designs (`Contract Assistant — Product UI`, 15 screens) by Claude and Codex, using React 18 + TypeScript + Vite + Tailwind 3. The tokens in `frontend/tailwind.config.js` come from the design system page.

## Original decision
The frontend is whatever Lovable generates: React + Vite + Tailwind + React Router. It uses
**TypeScript (`.tsx`) and shadcn/ui if Lovable defaults to them**. The empty `.jsx`
placeholders that were in `frontend/` are not a constraint, and Lovable's export replaces
the `frontend/` directory.

## Rules
- API calls live in one module, `src/lib/api.ts`, with types matching `docs/api/`.
- The original plan had a mock-data mode for the Lovable phase. It was not needed once the frontend was built against the running backend, so it does not exist. Tests use fixtures in the `docs/api/` shapes (`src/test/fixtures.ts`).
- No date arithmetic in the frontend. Only formatting.

## Consequences
- shadcn/ui was not used; the small component set in `src/components/ui/` follows the design system directly.
- The frontend has its own tests (Vitest + Testing Library), ESLint and Prettier, run by `make test` and `make lint`.
