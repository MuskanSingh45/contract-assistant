"""Load fixtures and score pipeline outputs. The runner is scripts/evaluate_ai.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai.evaluation.metrics import score_sample, summarize

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "contracts" / "fixtures" / "expected-extractions"
RESULTS = Path(__file__).resolve().parent / "results"


def load_fixtures(names: list[str] | None = None) -> dict[str, dict[str, Any]]:
    out = {}
    for path in sorted(FIXTURES.glob("*.json")):
        if names and path.stem not in names:
            continue
        out[path.stem] = json.loads(path.read_text())
    return out


def evaluate(fixtures: dict[str, dict], actual: dict[str, dict]) -> dict[str, Any]:
    """`actual[name]` is the sample's output dict (see scripts/evaluate_ai.py collect())."""
    scores = {name: score_sample(fixtures[name], actual[name]) for name in fixtures if name in actual}
    return {"samples": scores, "summary": summarize(list(scores.values()))}
