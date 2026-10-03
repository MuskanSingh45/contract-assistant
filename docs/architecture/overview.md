# Architecture Overview

## System

User
→ React + JavaScript frontend (Vite, Tailwind)
→ FastAPI REST API
→ application services
→ SQLite and AI pipeline
→ Ollama/Qwen3-8B

Stack: [ADR 001](../decisions/001-stack.md).

## Major responsibilities

### Frontend

Presentation, navigation, upload UX, review UX, and source display.

### Backend

API, orchestration, validation, business rules, deterministic date calculation, persistence.

### AI

Document understanding, structured extraction, ambiguity/conflict identification, and source association.

### Database

Contracts, versions, document segments, extracted items, obligations, calculated renewals, citations, reviews, clarification questions, version changes.

## Principle

Separate AI interpretation from deterministic application behavior.

## Detailed docs

- [system-architecture.md](system-architecture.md)
- [backend-architecture.md](backend-architecture.md)
- [data-flow.md](data-flow.md)
- [date-calculation.md](date-calculation.md)
- [deployment.md](deployment.md)
