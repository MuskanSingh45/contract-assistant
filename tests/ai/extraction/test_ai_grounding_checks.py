"""Deterministic grounding checks added after the real-model evaluation (docs/ai/pipeline.md §4)."""

from ai.validators.extraction_validator import (
    check_value_against_citations,
    is_permission_only,
    number_and_unit_in_text,
    number_words,
)


def test_number_words():
    assert {"90", "ninety"} <= number_words(90)
    assert {"45", "forty-five", "forty five"} <= number_words(45)
    assert "twelve" in number_words(12)


def test_number_and_unit_must_both_appear():
    assert number_and_unit_in_text(90, "days", "at least ninety (90) days before the expiration")
    assert number_and_unit_in_text(30, "business_days", "thirty (30) business days before the end")
    assert not number_and_unit_in_text(2, "days", "deliver a project status report every two weeks")
    assert not number_and_unit_in_text(90, "days", "at least sixty (60) days before")
    assert not number_and_unit_in_text(9, "days", "ninety (90) days")  # '9' inside '90' is not a match


def test_invented_notice_period_is_dropped():
    keep, _, _ = check_value_against_citations(
        "notice_period",
        {"value": 2, "unit": "days", "anchor": "other", "purpose": "termination"},
        ["Consultant shall deliver a project status report to Client every two weeks."],
    )
    assert keep is False


def test_supported_notice_period_is_kept():
    keep, value, _ = check_value_against_citations(
        "notice_period",
        {
            "value": 90,
            "unit": "days",
            "anchor": "expiration_date",
            "purpose": "non_renewal",
        },
        ["written notice of non-renewal at least ninety (90) days before the expiration of the then-current term"],
    )
    assert keep and value["anchor"] == "expiration_date"


def test_unsupported_renewal_period_is_cleared():
    keep, value, note = check_value_against_citations(
        "renewal_terms",
        {"type": "automatic", "period_value": 12, "period_unit": "months"},
        ["This Agreement renews automatically unless terminated."],
    )
    assert keep and value["period_value"] is None and value["type"] == "automatic" and note


def test_permission_is_not_an_obligation():
    assert is_permission_only(
        ["Customer may inspect Provider's warehouse facilities upon ten (10) days' prior notice."]
    )
    assert not is_permission_only(["Provider shall deliver an invoice within five (5) days."])
    assert not is_permission_only(["Customer may request reports, and Provider shall deliver them."])
