# Deployment

## MVP: local only
| Process | Command | Port |
|---|---|---|
| Ollama (native, **not Docker**: Docker on macOS has no GPU/Metal access) | `ollama serve` + `ollama pull qwen3:8b` | 11434 |
| Backend | `uvicorn backend.main:app --reload` (repo root) | 8000 |
| Frontend | `npm run dev` in `frontend/` | 5173 |

SQLite file `data/app.db`, logs in `data/logs/` and uploads in `uploads/` are created at runtime and git-ignored.

## Configuration
All configuration is via environment variables. See `.env.example`. Do not commit `.env`.

## Hardware note
Qwen3-8B (Q4) needs about 6 GB RAM plus the KV cache. With `OLLAMA_NUM_CTX=16384`, plan on
16 GB of system RAM. Expect 1–5 minutes per contract on a laptop.

Docker and cloud deployment are out of scope for the MVP.
