from ai.pipeline.clarification import (
    FIELD_LABELS,
    ambiguity_question,
    conflict_question,
    display_value,
    missing_term_question,
)


def test_display_values():
    assert (
        display_value(
            "notice_period",
            {
                "value": 90,
                "unit": "days",
                "anchor": "expiration_date",
                "purpose": "non_renewal",
            },
        )
        == "90 days before expiration (non-renewal)"
    )
    assert (
        display_value(
            "notice_period",
            {
                "value": 10,
                "unit": "business_days",
                "anchor": "renewal_date",
                "purpose": "other",
            },
        )
        == "10 business days before renewal"
    )
    assert (
        display_value(
            "notice_period",
            {"value": 30, "unit": "days", "anchor": "other", "purpose": "termination"},
        )
        == "30 days (termination)"
    )
    assert (
        display_value(
            "renewal_terms",
            {"type": "automatic", "period_value": 12, "period_unit": "months"},
        )
        == "Automatic, 12 months"
    )
    assert (
        display_value(
            "renewal_terms",
            {"type": "automatic", "period_value": 1, "period_unit": "years"},
        )
        == "Automatic, 1 year"
    )
    assert (
        display_value(
            "renewal_terms",
            {"type": "optional", "period_value": None, "period_unit": None},
        )
        == "Optional"
    )
    assert display_value("party", {"name": "Acme Corporation", "role": "customer"}) == "Acme Corporation (customer)"
    assert display_value("party", {"name": "Acme Corporation", "role": None}) == "Acme Corporation"
    assert display_value("effective_date", {"date_text": "January 31, 2025", "date": "2025-01-31"}) == "2025-01-31"
    assert display_value("expiration_date", {"date_text": "end of 2026", "date": None}) == "end of 2026"
    assert display_value("initial_term", {"value": 2, "unit": "years"}) == "2 years"
    assert (
        display_value("termination_clause", {"summary": "Either party may terminate for breach."})
        == "Either party may terminate for breach."
    )


def test_conflict_question_matches_template():
    q = conflict_question("notice_period", [("90 days", "3.2 Renewal"), ("60 days", "12.1 Notices")])
    assert q == (
        "Two sections specify different notice periods (90 days in 3.2 Renewal, 60 days in 12.1 Notices). "
        "Which provision should be treated as the applicable notice period rule?"
    )
    q3 = conflict_question("renewal_terms", [("A", None), ("B", "2"), ("C", None)])
    assert q3.startswith("Three sections specify different renewal terms (A, B in 2, C).")


def test_ambiguity_and_missing_questions():
    assert ambiguity_question("expiration_date", "2027-01-31", "Year is unclear.") == (
        "The expiration date may be ambiguous: Year is unclear. "
        "Please confirm or correct the extracted value '2027-01-31'."
    )
    assert missing_term_question().startswith("No expiration date or initial term was found.")
    assert FIELD_LABELS["notice_period"] == "notice period"
