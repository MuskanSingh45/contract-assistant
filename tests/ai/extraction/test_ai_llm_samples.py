"""Real-model check on the sample contracts (needs Ollama: pytest -m llm)."""

import json
import time

import pytest

from ai.pipeline.conflict_detection import normalize_party_name
from ai.pipeline.orchestrator import analyze
from tests.ai.sample_segments import ROOT, load_sample

FIXTURES = ROOT / "contracts" / "fixtures" / "expected-extractions"


def _values(result, field):
    return [i.value for i in result.items if i.field_name == field]


def _run(name: str):
    expected = json.loads((FIXTURES / f"{name}.json").read_text())
    started = time.monotonic()
    result = analyze(load_sample(expected["sample"]))
    print(f"\n{name}: {time.monotonic() - started:.1f}s stats={result.stats}")
    for item in result.items:
        print("  ", item.field_name, item.value, item.confidence)
    for obl in result.obligations:
        print(
            "   obligation:",
            obl.description,
            "|",
            obl.responsible_party,
            obl.frequency,
            obl.due_rule,
        )
    for clq in result.clarifications:
        print("   clarification:", clq.kind, clq.question)
    return expected, result


def _check_common(expected, result):
    fields = expected["fields"]
    parties = {normalize_party_name(v["name"]) for v in _values(result, "party")}
    assert parties >= {normalize_party_name(p["name"]) for p in fields["party"]}
    for field in ("effective_date", "expiration_date"):
        dates = {v["date"] for v in _values(result, field)}
        for exp in fields[field]:
            if not exp.get("optional"):
                assert exp["date"] in dates, field
    renewals = _values(result, "renewal_terms")
    assert fields["renewal_terms"][0] in renewals
    assert _values(result, "initial_term") == []
    assert result.stats["dropped_unsupported"] == 0


@pytest.mark.llm
def test_real_model_on_acme_and_globex():
    expected, acme = _run("acme-services-agreement")
    _check_common(expected, acme)
    notices = [v for v in _values(acme, "notice_period") if v["anchor"] != "other"]
    assert [(n["value"], n["unit"], n["anchor"]) for n in notices] == [(90, "days", "expiration_date")]
    assert [c for c in acme.clarifications if c.kind == "conflict"] == []
    descriptions = [o.description.lower() for o in acme.obligations]
    assert any("report" in d for d in descriptions)
    assert any("insurance" in d for d in descriptions)
    assert not any("terminat" in d for d in descriptions)

    expected, globex = _run("globex-hosting-agreement")
    _check_common(expected, globex)
    conflicts = [c for c in globex.clarifications if c.kind == "conflict"]
    assert [c.field_name for c in conflicts] == ["notice_period"]
    values = sorted(globex.items[i].value["value"] for i in conflicts[0].option_indexes)
    assert values == [60, 90]
