import os
import tempfile
from pathlib import Path

# Configure an isolated database/upload dir BEFORE backend.core.config is imported.
_TMP = Path(tempfile.mkdtemp(prefix="contract-assistant-tests-"))
os.environ["DATABASE_PATH"] = str(_TMP / "test.db")
os.environ["UPLOAD_DIR"] = str(_TMP / "uploads")
os.environ["LOG_FILE"] = ""
os.environ["LLM_PROVIDER"] = "ollama"  # tests never use a hosted model, whatever .env says
os.environ["LLM_FALLBACK_PROVIDER"] = ""  # and never fall back to it
