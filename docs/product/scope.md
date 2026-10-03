# Scope

## MVP: must have
- React/Vite/TypeScript frontend (built in-repo; [ADR 008](../decisions/008-frontend-language.md))
- FastAPI backend
- SQLite database
- PDF/DOCX upload and text extraction (text-based documents only)
- Qwen3-8B through Ollama
- Structured AI extraction: parties, effective/expiration date, initial term, renewal terms, notice period, termination clause summary
- Obligation extraction with responsible party and due rule
- Citation grounding (segment + verified quote)
- Confidence
- Human review (approve/edit/reject with history)
- Deterministic date calculation (notice deadline, term roll-forward, next obligation due date)
- Conflict detection and clarification questions (deterministic)
- Version tracking and comparison with the previous version

## MVP: simplified
- Local deployment (three processes, no Docker)
- Analysis in a FastAPI background task (no job queue)
- Source drawer instead of a PDF viewer
- Termination clauses: one-sentence summary only, with no termination date calculation
- Obligation due dates: next occurrence only, with no recurring schedule
- Business days: weekends only, no holiday calendars
- Version comparison: field-level and obligation-level changes only, with no clause-level text diff

## Deferred (placeholders deliberately removed; do not build for the MVP)
- AI contract summarization
- LLM-based conflict detection / clarification generation
- Docker / docker-compose
- Copying review decisions forward to a new version

## Out of scope
- Authentication, multi-user, RBAC
- Cloud deployment
- OCR (scanned PDFs fail with `NO_EXTRACTABLE_TEXT`)
- Email/calendar integrations and reminders
- Legal advice or legal interpretation
- Complex dashboards/analytics
- Advanced PDF viewer
- Production monitoring
- Billing
