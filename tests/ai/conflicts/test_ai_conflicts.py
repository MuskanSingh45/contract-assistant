from ai.pipeline.orchestrator import analyze
from ai.types import Segment
from tests.ai.fake_llm import FakeClient, cand, obligation, terms

S1 = Segment(
    1,
    1,
    "1. Parties",
    'Between Globex Inc. ("Client") and Initech Hosting LLC ("Provider").',
)
S2 = Segment(
    2,
    1,
    "3.2 Renewal",
    "The Agreement expires on December 31, 2026 and renews automatically "
    "unless notice is given at least ninety (90) days prior to expiration.",
)
S3 = Segment(
    3,
    2,
    "12.1 Notices",
    "Any notice of non-renewal must be delivered no later than sixty (60) "
    "days before the expiration date. This Agreement ends on December 30, 2026.",
)
S4 = Segment(
    4,
    2,
    "7.1 Termination",
    "Either party may terminate upon thirty (30) days' written notice "
    "if the other party materially breaches this Agreement.",
)

EXP_31 = {"date_text": "December 31, 2026", "date": "2026-12-31"}
EXP_30 = {"date_text": "December 30, 2026", "date": "2026-12-30"}


def notice(days, anchor="expiration_date", purpose="non_renewal"):
    return {"value": days, "unit": "days", "anchor": anchor, "purpose": purpose}


def test_two_expiration_dates_conflict_with_two_options():
    client = FakeClient(
        terms=[
            terms(
                expiration_date=[
                    cand(EXP_31, "S2", "expires on December 31, 2026"),
                    cand(EXP_30, "S3", "ends on December 30, 2026"),
                ]
            )
        ]
    )
    result = analyze([S1, S2, S3], client=client)
    (clq,) = result.clarifications
    assert clq.kind == "conflict" and clq.field_name == "expiration_date"
    assert [result.items[i].value["date"] for i in clq.option_indexes] == [
        "2026-12-31",
        "2026-12-30",
    ]
    assert len(clq.citations) == 2
    assert clq.question == (
        "Two sections specify different expiration dates (2026-12-31 in 3.2 Renewal, "
        "2026-12-30 in 12.1 Notices). Which provision should be treated as the applicable "
        "expiration date rule?"
    )


def test_same_value_in_two_windows_merges_without_conflict(monkeypatch):
    monkeypatch.setenv("EXTRACTION_WINDOW_TOKENS", "40")  # forces one segment per window
    client = FakeClient(
        terms=[
            terms(expiration_date=[cand(EXP_31, "S2", "expires on December 31, 2026", "medium")]),
            terms(
                expiration_date=[
                    cand(
                        {"date_text": "31 December 2026", "date": "2026-12-31"},
                        "S3",
                        "expiration date",
                        "high",
                    )
                ]
            ),
        ],
        obligations=[
            {
                "obligations": [
                    obligation(
                        "Submit quarterly report",
                        "Initech Hosting LLC",
                        "S2",
                        "ninety (90) days",
                    )
                ]
            },
            {
                "obligations": [
                    obligation(
                        "Submit the quarterly report",
                        "initech hosting llc",
                        "S3",
                        "sixty (60) days",
                    )
                ]
            },
        ],
    )
    progress = []
    result = analyze([S2, S3], client=client, on_progress=lambda *a: progress.append(a))
    assert result.stats["windows"] == 2
    assert progress == [
        ("extracting", 1, 2),
        ("extracting", 2, 2),
        ("validating", 0, 0),
    ]
    (item,) = result.items
    assert item.confidence == "high"
    assert [c.segment_seq for c in item.citations] == [2, 3]
    assert result.clarifications == []
    (obl,) = result.obligations
    assert [c.segment_seq for c in obl.citations] == [2, 3]


def test_two_parties_do_not_conflict():
    client = FakeClient(
        terms=[
            terms(
                parties=[
                    cand({"name": "Globex Inc.", "role": "client"}, "S1", "Globex Inc."),
                    cand(
                        {"name": "Initech Hosting LLC", "role": "provider"},
                        "S1",
                        "Initech Hosting LLC",
                    ),
                    cand(
                        {"name": "GLOBEX, Inc", "role": "Client"},
                        "S1",
                        'Globex Inc. ("Client")',
                    ),
                ]
            )
        ]
    )
    result = analyze([S1], client=client)
    assert [i.field_name for i in result.items] == ["party", "party"]
    assert result.items[1].value == {"name": "Initech Hosting LLC", "role": "provider"}
    assert result.clarifications == []


def test_notice_90_vs_60_conflicts_regardless_of_purpose():
    client = FakeClient(
        terms=[
            terms(
                notice_period=[
                    cand(
                        notice(90, purpose="termination"),
                        "S2",
                        "at least ninety (90) days prior to expiration",
                    ),
                    cand(
                        notice(60),
                        "S3",
                        "no later than sixty (60) days before the expiration date",
                    ),
                ]
            )
        ]
    )
    result = analyze([S2, S3], client=client)
    (clq,) = result.clarifications
    assert clq.field_name == "notice_period" and clq.option_indexes == [0, 1]
    assert "90 days before expiration (termination) in 3.2 Renewal" in clq.question
    assert "60 days before expiration (non-renewal) in 12.1 Notices" in clq.question


def test_same_notice_with_different_purpose_merges():
    client = FakeClient(
        terms=[
            terms(
                notice_period=[
                    cand(
                        notice(90, purpose="termination"),
                        "S2",
                        "ninety (90) days prior to expiration",
                    ),
                    cand(notice(90), "S2", "at least ninety (90) days"),
                ]
            )
        ]
    )
    result = analyze([S2], client=client)
    assert len(result.items) == 1 and result.clarifications == []


def test_notice_with_anchor_other_does_not_conflict():
    client = FakeClient(
        terms=[
            terms(
                notice_period=[
                    cand(
                        notice(90),
                        "S2",
                        "at least ninety (90) days prior to expiration",
                    ),
                    cand(
                        notice(30, anchor="other", purpose="termination"),
                        "S4",
                        "thirty (30) days' written notice",
                    ),
                ]
            )
        ]
    )
    result = analyze([S2, S4], client=client)
    assert len(result.items) == 2
    assert result.clarifications == []


def test_notice_anchored_to_expiration_without_support_becomes_other():
    client = FakeClient(
        terms=[
            terms(
                notice_period=[
                    cand(
                        notice(90),
                        "S2",
                        "at least ninety (90) days prior to expiration",
                    ),
                    cand(
                        notice(30, purpose="termination"),
                        "S4",
                        "Either party may terminate upon thirty (30) days' written notice",
                    ),
                ]
            )
        ]
    )
    result = analyze([S2, S4], client=client)
    assert result.items[1].value["anchor"] == "other"
    assert result.clarifications == []


def test_ambiguity_clarification_only_for_date_inputs_outside_conflicts():
    client = FakeClient(
        terms=[
            terms(
                renewal_terms=[
                    cand(
                        {
                            "type": "automatic",
                            "period_value": 1,
                            "period_unit": "years",
                        },
                        "S2",
                        "renews automatically",
                        note="Renewal period is implied.",
                    )
                ],
                termination_clause=[
                    cand(
                        {"summary": "Terminate for breach."},
                        "S4",
                        "materially breaches",
                        note="Cure period unclear.",
                    )
                ],
            )
        ]
    )
    result = analyze([S2, S4], client=client)
    (clq,) = result.clarifications
    assert clq.kind == "ambiguity" and clq.field_name == "renewal_terms" and clq.option_indexes == [0]
    # The quoted text never states the period, so the grounding check clears "1 year".
    assert clq.question == (
        "The renewal terms may be ambiguous: Renewal period is implied. "
        "Renewal period not found in quoted text. "
        "Please confirm or correct the extracted value 'Automatic'."
    )
    assert result.items[0].confidence == "medium"
