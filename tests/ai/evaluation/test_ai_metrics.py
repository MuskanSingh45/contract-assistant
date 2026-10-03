"""Unit tests for the AI evaluation scoring (ai/evaluation/metrics.py). No model needed."""

from ai.evaluation.metrics import (
    match_field,
    match_obligations,
    norm_name,
    score_sample,
    summarize,
)


def test_norm_name_ignores_case_punctuation_and_suffix():
    assert norm_name("Example Services Ltd.") == norm_name("example services") == "example services"
    assert norm_name("Globex Inc.") == "globex"


def test_match_field_found_missing_hallucinated_and_optional():
    r = match_field(
        "notice_period",
        [{"value": 90, "unit": "days"}],
        [{"value": 90, "unit": "days", "anchor": "x"}],
    )
    assert (r["found"], r["missing"], r["hallucinated"]) == (1, [], [])
    r = match_field(
        "notice_period",
        [{"value": 90, "unit": "days"}],
        [{"value": 60, "unit": "days"}],
    )
    assert r["found"] == 0 and len(r["missing"]) == 1 and len(r["hallucinated"]) == 1
    r = match_field("termination_clause", [{"summary_contains": ["breach"], "optional": True}], [])
    assert r["missing"] == [] and r["expected_required"] == 0


def test_correct_empty_means_nothing_invented():
    assert match_field("expiration_date", [], [])["correct_empty"] is True
    r = match_field("expiration_date", [], [{"date": "2027-01-01"}])
    assert r["correct_empty"] is False and r["hallucinated"] == [{"date": "2027-01-01"}]


def test_obligations_attributes_and_rights():
    expected = [
        {
            "description_contains": ["report"],
            "responsible_party": "Vendor Ltd.",
            "frequency": "monthly",
            "due_rule": {"basis": "calendar_period_end", "offset_days": 10},
        }
    ]
    actual = [
        {
            "description": "Deliver monthly report",
            "responsible_party": "Vendor",
            "frequency": "monthly",
            "due_rule": {"basis": "calendar_period_end", "offset_days": 5},
        },
        {
            "description": "Customer may inspect facilities",
            "responsible_party": None,
            "frequency": None,
            "due_rule": None,
        },
    ]
    r = match_obligations(expected, actual, ["inspect"])
    assert r["found"] == 1 and r["attribute_checks"] == 3
    assert [e["attribute"] for e in r["attribute_errors"]] == ["due_rule"]
    assert r["rights_as_obligations"] == ["Customer may inspect facilities"]


def test_score_and_summary_end_to_end():
    fixture = {
        "fields": {"effective_date": [{"date": "2025-01-31"}], "expiration_date": []},
        "obligations": [{"description_contains": ["report"]}],
        "conflicts": [{"field_name": "notice_period"}],
        "renewal": {"notice_deadline": "2026-11-02"},
        "obligation_due_dates": {"report": "2026-10-30"},
    }
    actual = {
        "items": [
            {
                "field_name": "effective_date",
                "value": {"date": "2025-01-31"},
                "citation_statuses": ["verified"],
            }
        ],
        "obligations": [
            {
                "description": "Quarterly report",
                "due_date": "2026-10-30",
                "citation_statuses": ["approximate"],
            }
        ],
        "clarifications": [{"kind": "conflict", "field_name": "notice_period"}],
        "renewal": {"notice_deadline": "2026-11-02"},
    }
    s = score_sample(fixture, actual)
    assert s["conflicts"]["ok"] and not s["renewal_errors"] and not s["due_date_errors"]
    summary = summarize([s])
    assert summary["field_precision_pct"] == 100.0
    assert summary["missing_info_correct"] == "1/1"
    assert summary["date_results_ok"] == "1/1"
    assert summary["citations_verified_pct"] == 50.0
