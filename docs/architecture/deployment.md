# Deployment

## Online (free tiers)

| Part | Host | Address | Config |
|---|---|---|---|
| Frontend | Vercel | https://contract-assistant-flame.vercel.app | `frontend/vercel.json` (all routes → `index.html`); env `VITE_API_BASE_URL=https://contract-assistant-api-4qba.onrender.com/api` set in the Vercel project (Production) |
| Backend | Render free web service | https://contract-assistant-api-4qba.onrender.com | [`render.yaml`](../../render.yaml) |
| Model | Groq API, `qwen/qwen3.8-27b` | — | `LLM_PROVIDER=groq`, `GROQ_API_KEY` (Render dashboard, secret) |

Why this split: the frontend is static, the backend fits in Render's 512 MB, and no free host has
the ~16 GB of RAM Qwen3-8B needs. Hugging Face Docker Spaces were tried first, but they now require
a paid subscription (see `AGENT_USAGE.md`, mistake 12). The model provider is a setting
(`LLM_PROVIDER`), so the same code runs locally with Ollama.

### Backend on Render
- Created from the Blueprint (`render.yaml`): build `pip install -r requirements.txt`, start
  `python scripts/reset_dev.py && uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
- **Redeploy:** automatic on every push to `main`.
- `scripts/reset_dev.py` runs on each start because the free disk is not persistent: every
  restart begins with the demo data (Acme, Globex). Uploads last until the next restart.
- Free services sleep after 15 minutes without traffic and take about a minute to wake.
- `FRONTEND_ORIGIN` allows the Vercel address (CORS). `LOG_FILE` is empty, so logs go to the console and appear in Render's Logs tab, with request IDs.
- `GROQ_API_KEY` is marked `sync: false`: Render asks for it once and stores it as a secret.
- `WORKSPACES=true`: one database per browser workspace in `data/workspaces/`, each starting with the demo data ([ADR 009](../decisions/009-workspace-isolation.md)). Limits: `MAX_NEW_WORKSPACES_PER_HOUR=30` per address, `MAX_ANALYSES_PER_HOUR=20` per address and per workspace.
- Model routing: Groq is the primary and only provider online. Locally Ollama is primary and Groq can be the fallback (`LLM_FALLBACK_PROVIDER=groq`).

### Frontend on Vercel
- The Vercel project is linked to the GitHub repository with **Root Directory `frontend`**
  (framework: Vite), so **every push to `main` redeploys the frontend**, like the backend on Render.
- `VITE_API_BASE_URL=https://contract-assistant-api-4qba.onrender.com/api` is set once in the
  project (Production). It is read at build time, so changing it needs a redeploy.
- Manual deploy, if ever needed: `vercel deploy --prod` from the repository root.

### Applying `render.yaml` changes
Render auto-deploys **code** on every push, but changes to the blueprint's **environment
variables** are applied by a blueprint sync: Render dashboard → Blueprints →
contract-assistant-api → **Manual sync**. (Found when `WORKSPACES=true` reached the code but
not the running service.)

### Model on Groq
Free tier, no card: about 8,000 tokens per minute and 1,000 requests per day. The client waits
on HTTP 429 and retries; windows are 2,500 tokens. Settings and evaluation: [../ai/model-config.md](../ai/model-config.md),
[../testing/ai-evaluation.md](../testing/ai-evaluation.md). Uploaded contract text is sent to Groq, as the app's Help page states.

## Local
| Process | Command | Port |
|---|---|---|
| Ollama (native, **not Docker**: Docker on macOS has no GPU/Metal access) | `ollama serve` + `ollama pull qwen3:8b` | 11434 |
| Backend | `uvicorn backend.main:app --reload` (repo root) | 8000 |
| Frontend | `npm run dev` in `frontend/` | 5173 |

`make dev` starts all three. SQLite file `data/app.db`, logs in `data/logs/` and uploads in `uploads/` are created at runtime and git-ignored.

## Configuration
All configuration is via environment variables. See `.env.example`. Do not commit `.env` or any key.

## Hardware note (local)
Qwen3-8B (Q4) needs about 6 GB RAM plus the KV cache. With `OLLAMA_NUM_CTX=16384`, plan on
16 GB of system RAM. Expect 1–5 minutes per contract on a laptop.
