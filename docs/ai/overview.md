# AI Overview

The AI layer (`ai/`) extracts and interprets contract information using **Qwen3-8B via
Ollama**.

AI output is not trusted blindly. It passes JSON Schema validation, citation grounding,
business validation and confidence adjustment before the backend uses it. Conflicts,
clarifications and all date arithmetic are deterministic code.

| Doc | Topic |
|---|---|
| [pipeline.md](pipeline.md) | End-to-end flow, windowing, merging, hard rules |
| [extraction.md](extraction.md) | Output shapes, missing-info rule |
| [citation-and-review.md](citation-and-review.md) | Citation grounding and review actions |
| [confidence.md](confidence.md) | Confidence vs review status, downgrade rules |
| [conflict-detection.md](conflict-detection.md) | Deterministic conflict rule |
| [clarification.md](clarification.md) | Clarification triggers and templates |
| [prompts.md](prompts.md) | Prompt rules and versioning |
| [model-config.md](model-config.md) | Ollama settings (`num_ctx`, `think`, `format`) |
