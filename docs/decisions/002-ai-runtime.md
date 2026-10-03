# ADR 002 — AI Runtime

## Decision
Use Qwen3-8B through Ollama as the initial local model runtime.

## Constraint
Model output is not authoritative. It must be validated and processed by deterministic application code.

## Update (2026-10-03): hosted model for the online deployment
No free host has the ~16 GB of RAM Qwen3-8B needs (Hugging Face Docker Spaces now require a paid
plan). The runtime is therefore a setting, `LLM_PROVIDER`: `ollama` (default, local) or `groq`
(Groq's free OpenAI-compatible API, `qwen/qwen3.8-27b`), used only by the online deployment.
Prompts, schemas, grounding checks and review are the same for both. Evaluation on the sample set:
100% recall, 97.1% precision, 0 invented values ([ai-evaluation.md](../testing/ai-evaluation.md)).
Trade-off: online, contract text is sent to Groq, which the README and the Help page state.
