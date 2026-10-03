# AI Architecture

Summary only. The detailed design is in [docs/ai/](../ai/pipeline.md).

- **Model:** Qwen3-8B via Ollama (local runs) or Qwen `qwen3.8-27b` via Groq (online deployment), selected by `LLM_PROVIDER`; pretrained, no training. Config: [../ai/model-config.md](../ai/model-config.md).
- **Package:** `ai/`, called by `backend/services/analysis_service.py`. It has no database access.

## The model is responsible for
- Interpreting contract language
- Extracting structured fields (parties, dates, term, renewal, notice, termination summary)
- Extracting obligations, responsible parties and due rules
- Flagging ambiguity on an item (`ambiguity_note`)
- Pointing at evidence: segment label + verbatim quote

## The model is NOT responsible for (deterministic code is)
- Date arithmetic: `backend/utils/dates.py`
- Page numbers and section names: taken from parsed segments
- Deciding whether a quote is real: citation validator
- Conflict detection between candidates: `ai/pipeline/conflict_detection.py`, in code
- Clarification question text: templates
- Database state, review status, version persistence
