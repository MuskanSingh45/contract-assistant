# Model Configuration

## Model and runtime
Two providers behind the same client interface (`ai/llm/client.py`, `make_client()`), chosen by
`LLM_PROVIDER`. Both are pretrained Qwen models, not fine-tuned.

| `LLM_PROVIDER` | Runtime | Model | Used for |
|---|---|---|---|
| `ollama` (default) | Ollama, native install on the user's machine | `qwen3:8b` | Local runs (`make dev`). Contract text never leaves the machine |
| `groq` | Groq's hosted, OpenAI-compatible API (free tier) | `qwen/qwen3.8-27b` | The online deployment, where no free host can run the model. Contract text is sent to Groq |

The pipeline, prompts, schemas, grounding checks and review flow are identical for both.

## Environment

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_NUM_CTX=16384
OLLAMA_TIMEOUT_SECONDS=300          # request timeout for either provider
EXTRACTION_WINDOW_TOKENS=           # empty = 6000 (ollama) / 2500 (groq)
GROQ_API_KEY=                       # secret: .env or the host's dashboard only
GROQ_MODEL=qwen/qwen3.8-27b
GROQ_BASE_URL=https://api.groq.com/openai/v1
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

## Groq request settings (`ai/llm/groq_client.py`, `/chat/completions`)

| Setting | Value | Why |
|---|---|---|
| `response_format` | `json_schema` with the schema, `strict: false` | Strict mode fails on Groq for these schemas; the pipeline validates the output and retries once, as with Ollama |
| `temperature`, `seed` | `0`, `42` | Reproducible extraction |
| Rate limits | on HTTP 429, wait for `retry-after` (capped at 60 s), up to 6 times | The free tier allows about 8,000 tokens per minute and 1,000 requests per day; a contract finishes, just more slowly |
| Window size | 2,500 tokens | Keeps each call well inside the per-minute token limit |

Qwen on Groq returns plain JSON without `<think>` text; `clean_content()` would remove it anyway.

## Availability
- `GET /api/health` and `POST /analyze` check the configured provider: `GET {OLLAMA_BASE_URL}/api/tags` for Ollama, `GET {GROQ_BASE_URL}/models` for Groq.
- If the model is unavailable, the analysis fails with `AI_UNAVAILABLE`. It never fabricates results.

## Swapping models
`OLLAMA_MODEL` and `GROQ_MODEL` are configurable. Any model must pass `scripts/evaluate_ai.py`
on the `contracts/` set before being used for the demo (run it with `LLM_PROVIDER=groq` for the
hosted model). Results for both providers: [../testing/ai-evaluation.md](../testing/ai-evaluation.md).
