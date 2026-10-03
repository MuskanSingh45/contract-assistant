# System Architecture

## 1. Architecture

The application consists of four major layers:

Frontend
   ↓
FastAPI Backend
   ↓
Application Services
   ↓
Database + AI Pipeline

---

## 2. High-Level Architecture

                    ┌──────────────────┐
                    │      User        │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ React + JS (Vite)│
                    │ Frontend         │
                    └────────┬─────────┘
                             │ REST API
                             ▼
                    ┌──────────────────┐
                    │ FastAPI (Python) │
                    └───────┬────┬─────┘
                            │    │
                  ┌─────────┘    └─────────┐
                  ▼                        ▼
          ┌──────────────┐          ┌──────────────┐
          │ SQLite       │          │ AI Pipeline  │
          │ Database     │          └───────┬──────┘
          └──────────────┘                  │
                                           ▼
                                    ┌──────────────┐
                                    │ Ollama       │
                                    │ Qwen3-8B     │
                                    └──────────────┘

---

Stack details: [ADR 001](../decisions/001-stack.md).

---

## 3. Responsibilities

### Frontend

Responsible for:

- User interface
- Navigation
- Upload interaction
- Contract views
- Review interface
- Obligation views
- Renewal views
- Source citation display

Frontend does not perform authoritative contract calculations.

---

### Backend

Responsible for:

- API
- File management
- Application workflow
- Validation
- Database persistence
- Date calculations
- AI pipeline orchestration

---

### AI Layer

Responsible for:

- Document understanding
- Information extraction
- Clause identification
- Obligation extraction
- Ambiguity flagging
- Evidence selection (segment + quote). Page/section and validation are done by code.

---

### Database

Responsible for:

- Contracts
- Versions
- Extracted information
- Obligations
- Renewals (calculated)
- Citations
- Reviews
- Clarification questions
- Version changes

---

## 4. Critical Architectural Rule

AI interprets and extracts.

Application code validates and calculates.

For example:

Contract:

"Notice must be provided at least 90 days before expiration."

AI output:

{
  "value": 90,
  "unit": "days",
  "anchor": "expiration_date"
}

Python calculates the actual date. See [date-calculation.md](date-calculation.md).

The LLM must not be responsible for authoritative date arithmetic.

---

## 5. Source of Truth

The repository is the source of truth.

Documentation under:

docs/

defines the product, architecture, API, database, AI pipeline, and
frontend contracts.