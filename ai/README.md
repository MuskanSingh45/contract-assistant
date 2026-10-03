# ai/

The extraction pipeline around Qwen models: Qwen3-8B via Ollama locally, or `qwen/qwen3.8-27b` via Groq for the online deployment (`LLM_PROVIDER`). It has no database access. The backend
calls `ai.pipeline.orchestrator.analyze(segments, on_progress=...)`. The interface is in
`.ai/agents/ai.md`.

| Path | Purpose |
|---|---|
| `llm/` | `make_client()` provider switch; Ollama client (`format` = JSON Schema, `think=false`, `num_ctx`); Groq client (OpenAI-compatible, `json_schema` response format, 429 retry); model config; structured output parsing + retry |
| `pipeline/` | orchestrator (windowing, merge), terms extraction, obligation extraction, deterministic conflict detection, clarification templates |
| `prompts/extraction/` | `terms.txt`, `obligations.txt` (versioned via a `# version:` header) |
| `schemas/` | `extraction.json`, `obligation.json`: JSON Schemas for model output |
| `validators/` | extraction (schema + business), citation grounding, confidence downgrades |
| `evaluation/` | evaluator + metrics against `contracts/fixtures/` |

Design: `docs/ai/`. Status: implemented and tested (`pytest tests/ai`; the real-model test is `-m llm`).
About 2 minutes per short contract on an M1 Pro (about 17 tokens/s).
