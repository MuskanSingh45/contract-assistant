"""Prompt/schema loading and structured-output parsing with one repair retry."""

from __future__ import annotations

import json
import logging
import re
from functools import cache
from pathlib import Path
from typing import Any

from ai.errors import InvalidAIOutput
from ai.llm.client import LLMClient
from ai.validators.extraction_validator import schema_error

logger = logging.getLogger(__name__)

AI_ROOT = Path(__file__).resolve().parent.parent
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")
_VERSION = re.compile(r"^#\s*version:\s*(\S+)\s*$")


@cache
def load_schema(name: str) -> dict[str, Any]:
    return json.loads((AI_ROOT / "schemas" / name).read_text(encoding="utf-8"))


@cache
def load_prompt(name: str) -> tuple[str, str]:
    """Return (version, template) for ai/prompts/<name>; the `# version:` line is stripped."""
    lines = (AI_ROOT / "prompts" / name).read_text(encoding="utf-8").splitlines()
    match = _VERSION.match(lines[0]) if lines else None
    if not match:
        raise ValueError(f"Prompt {name} is missing its '# version:' header")
    return match.group(1), "\n".join(lines[1:]).strip() + "\n"


def render_prompt(template: str, segments_text: str) -> str:
    return template.replace("{{segments}}", segments_text)


def clean_content(content: str) -> str:
    """Remove <think> blocks and markdown fences that some model versions emit."""
    return _FENCE.sub("", _THINK.sub("", content).strip()).strip()


def parse_and_validate(content: str, schema: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """Return (data, "") on success or (None, error message) on failure."""
    try:
        data = json.loads(clean_content(content))
    except json.JSONDecodeError as exc:
        return None, f"Output is not valid JSON: {exc}"
    error = schema_error(data, schema)
    if error:
        return None, error
    return data, ""


def request_structured(client: LLMClient, prompt: str, schema: dict[str, Any], stats: dict[str, Any]) -> dict[str, Any]:
    """Call the model, validate against `schema`, retry once with a repair message.

    Raises InvalidAIOutput after the second failure.
    """
    messages = [{"role": "user", "content": prompt}]
    content = client.chat(messages, schema)
    data, error = parse_and_validate(content, schema)
    if data is not None:
        return data

    logger.warning("Model output failed validation (%s); retrying once", error, extra={"event": "llm.retry"})
    stats["retries"] = stats.get("retries", 0) + 1
    messages += [
        {"role": "assistant", "content": content},
        {
            "role": "user",
            "content": (
                f"Your previous answer was invalid: {error}\n"
                "Return the complete corrected JSON object that matches the schema. "
                "Keep every quote verbatim and at most 300 characters."
            ),
        },
    ]
    content = client.chat(messages, schema)
    data, error = parse_and_validate(content, schema)
    if data is None:
        raise InvalidAIOutput(f"Model output failed validation after retry: {error}")
    return data
