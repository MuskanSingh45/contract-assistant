# State Management

Keep MVP state management simple.

Use local component state for UI-only state and a small shared store/context only where cross-page state is needed.

After backend integration, API/server state is authoritative for:
- contracts
- contract details
- analysis status
- obligations
- renewals
- reviews
- versions
- clarifications
- every calculated date and `days_until_*` value

UI state includes:
- active tab
- source drawer
- selected review item
- upload progress
- filters
- search query
- selected version (in the URL)

Do not duplicate authoritative date calculations in frontend state.
