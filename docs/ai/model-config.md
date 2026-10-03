# Model Configuration

## Model and runtime
Qwen3-8B, served by Ollama (native install, not Docker). It is pretrained and not
fine-tuned.

## Environment

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_NUM_CTX=16384
OLLAMA_TIMEOUT_SECONDS=300
EXTRACTION_WINDOW_TOKENS=6000
```

## Request settings (`ai/llm/ollama_client.py`, `/api/chat`)

| Setting | Value | Why |
|---|---|---|
| `format` | the JSON Schema from `ai/schemas/*.json` | Constrained decoding, so output is valid JSON matching the schema |
| `think` | `false` | Qwen3 otherwise emits `<think>` reasoning, which is slow and breaks JSON parsing. Also add `/no_think` to the user message as a fallback for older Ollama versions. |
| `options.num_ctx` | `OLLAMA_NUM_CTX` (16384) | **Critical.** Ollama's default context is 2–4K tokens and it **silently truncates** longer input. The model would then see only part of the contract and invent the rest. |
| `options.temperature` | `0` | Reproducible extraction |
| `options.seed` | `42` | Reproducible extraction |
| `stream` | `false` | |

Budget per call: prompt (~1.5K tokens) + window (≤ 6K) + output (≤ 4K) < 16K.

Before sending, `ollama_client` estimates the prompt tokens (characters ÷ 4). If the
estimate exceeds 75% of `num_ctx`, it raises an error instead of letting Ollama truncate.

## Availability
- `GET /api/health` and `POST /analyze` check `GET {OLLAMA_BASE_URL}/api/tags` for the model.
- If the model is unavailable, the analysis fails with `AI_UNAVAILABLE`. It never fabricates results.

## Swapping models
`OLLAMA_MODEL` is configurable. Any model must pass `scripts/evaluate_ai.py` on the
`contracts/` set before being used for the demo.
