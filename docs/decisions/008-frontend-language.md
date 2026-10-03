# ADR 008 — Frontend Language and Ownership

## Status
Accepted (2026-10-03).

## Update (2026-10-03)
Lovable was dropped because of the deadline. The frontend is built in this repo from the product designs (`Contract Assistant — Product UI`, 15 screens) by Claude and Codex, using React 18 + TypeScript + Vite + Tailwind 3. The tokens in `frontend/tailwind.config.js` come from the design system page.

## Update (2026-10-03, later): JavaScript instead of TypeScript
At the developer's request, the frontend was converted from TypeScript to **JavaScript (`.js`/`.jsx`)**. The conversion only removed type annotations (with Sucrase), so the code and its behaviour are unchanged; all 54 frontend tests passed before and after. The API data shapes from `types.ts` are kept as **JSDoc typedefs** in `src/lib/types.js`, so they stay documented and editors still offer hints.

The build config was updated with it: Vite/Vitest configs as `.js`, `jsconfig.json` for the `@/` alias, and Tailwind now scans `.js`/`.jsx` (missing that left the app unstyled until a browser check caught it). Trade-off: no compile-time type checking. Behaviour is guarded by the Vitest suite and ESLint (`eslint-plugin-react`, `react-hooks`), both run by `make test`.

## Original decision
The frontend is whatever Lovable generates: React + Vite + Tailwind + React Router. It uses
**TypeScript (`.tsx`) and shadcn/ui if Lovable defaults to them**. The empty `.jsx`
placeholders that were in `frontend/` are not a constraint, and Lovable's export replaces
the `frontend/` directory.

## Rules
- API calls live in one module, `src/lib/api.js`, with data shapes (JSDoc typedefs in `src/lib/types.js`) matching `docs/api/`.
- The original plan had a mock-data mode for the Lovable phase. It was not needed once the frontend was built against the running backend, so it does not exist. Tests use fixtures in the `docs/api/` shapes (`src/test/fixtures.js`).
- No date arithmetic in the frontend. Only formatting.

## Consequences
- shadcn/ui was not used; the small component set in `src/components/ui/` follows the design system directly.
- The frontend has its own tests (Vitest + Testing Library), ESLint and Prettier, run by `make test` and `make lint`.
- The Update above supersedes the TypeScript choice; the Original decision is kept as history.
