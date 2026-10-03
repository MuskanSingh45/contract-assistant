import pytest

from ai.errors import InvalidAIOutput
from ai.pipeline.orchestrator import analyze, build_windows, format_segment
from ai.types import Segment
from tests.ai.fake_llm import FakeClient, cand, obligation, terms

SEG = Segment(
    1,
    1,
    None,
    'This Agreement is entered into as of January 31, 2025 (the "Effective Date").',
)
EFFECTIVE = {"date_text": "January 31, 2025", "date": "2025-01-31"}
QUOTE = "as of January 31, 2025"


def test_valid_output_produces_items_and_metadata():
    client = FakeClient(
        terms=[terms(effective_date=[cand(EFFECTIVE, "S1", QUOTE)])],
        obligations=[{"obligations": [obligation("Do a thing", "Acme", "S1", QUOTE)]}],
    )
    result = analyze([SEG], client=client)
    (item,) = result.items
    assert (item.field_name, item.confidence, item.ambiguity_note) == (
        "effective_date",
        "high",
        None,
    )
    assert result.model_name == "fake-model"
    assert result.prompt_version.startswith("terms-v") and "+obligations-v" in result.prompt_version
    (obl,) = result.obligations
    assert obl.original_value["description"] == "Do a thing"
    assert obl.due_rule == {"basis": "calendar_period_end", "offset_days": 30}
    assert set(result.stats) >= {
        "windows",
        "retries",
        "dropped_unsupported",
        "citations_not_found",
        "seconds",
    }


def test_prompt_contains_segments_without_version_header_or_pages():
    client = FakeClient()
    analyze([SEG], client=client)
    prompt = client.calls[0][1][0]["content"]
    assert "# version" not in prompt
    assert "[S1]\nThis Agreement" in prompt
    assert "{{segments}}" not in prompt and "page" not in prompt.lower().split("segments")[-1]


def test_schema_failure_retries_once_then_succeeds():
    bad = terms(
        effective_date=[
            {
                "value": EFFECTIVE,
                "confidence": "certain",
                "evidence": [],
                "ambiguity_note": None,
            }
        ]
    )
    client = FakeClient(terms=[bad, terms(effective_date=[cand(EFFECTIVE, "S1", QUOTE)])])
    result = analyze([SEG], client=client)
    assert result.stats["retries"] == 1
    assert len(result.items) == 1
    retry_messages = client.calls[1][1]
    assert [m["role"] for m in retry_messages] == ["user", "assistant", "user"]
    assert "invalid" in retry_messages[-1]["content"]


def test_second_schema_failure_raises_invalid_output():
    client = FakeClient(terms=["not json at all", '{"parties": []}'])
    with pytest.raises(InvalidAIOutput):
        analyze([SEG], client=client)


def test_think_block_and_fences_are_stripped():
    import json

    content = "<think>hmm</think>\n```json\n" + json.dumps(terms()) + "\n```"
    result = analyze([SEG], client=FakeClient(terms=[content]))
    assert result.stats["retries"] == 0 and result.items == []


def test_invalid_calendar_date_is_dropped():
    bad = {"date_text": "February 30, 2025", "date": "2025-02-30"}
    result = analyze([SEG], client=FakeClient(terms=[terms(effective_date=[cand(bad, "S1", QUOTE)])]))
    assert result.items == []


def test_date_mismatch_sets_low_confidence_and_ambiguity():
    wrong = {"date_text": "January 31, 2025", "date": "2025-01-30"}
    result = analyze(
        [SEG],
        client=FakeClient(terms=[terms(effective_date=[cand(wrong, "S1", QUOTE, note="Odd.")])]),
    )
    (item,) = result.items
    assert item.confidence == "low"
    assert item.ambiguity_note == "Odd. Model date does not match quoted text"
    (clq,) = result.clarifications
    assert clq.kind == "ambiguity" and clq.field_name == "effective_date"


def test_unparseable_date_text_caps_medium():
    vague = {"date_text": "the first business day of 2025", "date": "2025-01-02"}
    result = analyze(
        [SEG],
        client=FakeClient(terms=[terms(effective_date=[cand(vague, "S1", QUOTE)])]),
    )
    assert result.items[0].confidence == "medium"


def test_initial_term_not_stated_in_text_is_dropped():
    seg = Segment(
        1,
        None,
        None,
        "The initial term shall commence on the Effective Date and expire on January 31, 2027.",
    )
    term = cand({"value": 2, "unit": "years"}, "S1", "expire on January 31, 2027")
    result = analyze([seg], client=FakeClient(terms=[terms(initial_term=[term])]))
    assert result.items == []


def test_windowing_never_splits_segments_and_respects_budget():
    segs = [Segment(i, None, "1. Sec" if i % 2 else None, "x" * 390) for i in range(1, 11)]
    windows = build_windows(segs, max_tokens=250)
    assert [s.seq for w in windows for s in w] == list(range(1, 11))
    assert all(len(w) == 2 for w in windows)
    assert format_segment(segs[0]) == "[S1] (1. Sec)\n" + "x" * 390
    assert format_segment(segs[1]).startswith("[S2]\n")


def test_evidence_from_other_window_is_discarded(monkeypatch):
    monkeypatch.setenv("EXTRACTION_WINDOW_TOKENS", "25")
    seg2 = Segment(2, None, None, "Expires on January 31, 2027.")
    exp = {"date_text": "January 31, 2027", "date": "2027-01-31"}
    client = FakeClient(terms=[terms(expiration_date=[cand(exp, "S2", "Expires on January 31, 2027")])])
    result = analyze([SEG, seg2], client=client)
    assert result.items == [] and result.stats["dropped_unsupported"] == 1


def test_analyze_without_a_client_uses_the_active_provider(monkeypatch):
    """The production path (no injected client) picks the provider via active_config()."""
    from ai.llm.model_config import load_config
    from ai.pipeline import orchestrator

    chosen = []
    monkeypatch.setattr(orchestrator, "active_config", lambda: chosen.append(1) or load_config())
    monkeypatch.setattr(orchestrator, "make_client", lambda config: FakeClient([]))
    orchestrator.analyze([])
    assert chosen == [1]
