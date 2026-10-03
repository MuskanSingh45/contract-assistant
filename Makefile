# Contract Obligation and Renewal Assistant
#
#   make setup   install everything (Python venv, frontend deps, .env, database + demo data, AI model)
#   make dev     start Ollama (if needed), backend :8000 and frontend :5173 together; Ctrl-C stops both
#   make test    backend/AI tests (pytest) + frontend tests (Vitest) + frontend ESLint
#   make lint    ruff (lint + format check) + ESLint + Prettier check
#   make fmt     auto-format Python (ruff) and frontend (Prettier)
#   make eval    real-model AI evaluation on the sample contracts (about 7 min; needs Ollama)
#   make reset   restore the demo database (Acme + Globex) before a demo

SHELL       := /bin/bash
VENV        := .venv
PY          := $(VENV)/bin/python
MODEL       ?= qwen3:8b
OLLAMA_URL  := http://localhost:11434

.PHONY: help setup dev test lint fmt eval reset ollama

help:
	@grep -E '^#   make' Makefile | sed 's/^#   //'

setup:
	@command -v python3 >/dev/null || { echo "python3 (3.11+) is required"; exit 1; }
	@command -v npm >/dev/null || { echo "Node.js/npm is required"; exit 1; }
	@test -x $(PY) || python3 -m venv $(VENV)
	@echo "==> Python dependencies"
	@$(PY) -m pip install -q --upgrade pip
	@$(PY) -m pip install -q -r requirements.txt
	@echo "==> Frontend dependencies"
	@cd frontend && npm install --silent
	@test -f .env || cp .env.example .env
	@test -f frontend/.env || cp frontend/.env.example frontend/.env
	@echo "==> Database"
	@if [ -f data/app.db ]; then $(PY) scripts/setup.py; else $(PY) scripts/reset_dev.py; fi
	@echo "==> AI model ($(MODEL))"
	@if command -v ollama >/dev/null; then \
	  $(MAKE) --no-print-directory ollama && ollama pull $(MODEL); \
	else \
	  echo "   Ollama not installed: get it from https://ollama.com, then run 'ollama pull $(MODEL)'"; \
	fi
	@echo "Setup complete. Run 'make dev'."

# Start Ollama if it is not already answering (macOS app if installed, else 'ollama serve').
ollama:
	@if curl -s -m 2 $(OLLAMA_URL)/api/tags >/dev/null; then exit 0; fi; \
	if ! command -v ollama >/dev/null; then echo "!! Ollama not installed: analysis will be unavailable"; exit 0; fi; \
	echo "==> Starting Ollama"; \
	if [ -d /Applications/Ollama.app ]; then open -g -a Ollama; else (nohup ollama serve >/tmp/ollama.log 2>&1 &); fi; \
	for i in $$(seq 1 30); do curl -s -m 2 $(OLLAMA_URL)/api/tags >/dev/null && exit 0; sleep 1; done; \
	echo "!! Ollama did not start within 30s: analysis will be unavailable"

dev: ollama
	@test -x $(PY) || { echo "Run 'make setup' first"; exit 1; }
	@echo "==> Backend  http://localhost:8000/docs"
	@echo "==> Frontend http://localhost:5173   (Ctrl-C stops both)"
	@trap 'kill 0' INT TERM EXIT; \
	$(VENV)/bin/uvicorn backend.main:app --port 8000 --reload --no-access-log \
	  --reload-dir backend --reload-dir ai --reload-dir db & \
	(cd frontend && npm run dev -- --port 5173 --strictPort) & \
wait

test:
	@echo "==> Backend + AI tests"
	@$(PY) -m pytest -q -p no:warnings
	@echo "==> Frontend tests"
	@cd frontend && npx vitest run
	@cd frontend && npx eslint . && echo "frontend lint ok"

lint:
	@$(VENV)/bin/ruff check .
	@$(VENV)/bin/ruff format --check .
	@cd frontend && npx eslint . && npx prettier --check src

fmt:
	@$(VENV)/bin/ruff check --fix .
	@$(VENV)/bin/ruff format .
	@cd frontend && npx prettier --write src

eval: ollama
	@$(PY) scripts/evaluate_ai.py

reset:
	@$(PY) scripts/reset_dev.py
	@rm -rf uploads/ctr_*
	@echo "Demo data restored."
