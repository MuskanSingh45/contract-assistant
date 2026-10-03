from ai.pipeline.orchestrator import analyze
from ai.types import Segment
from ai.validators.citation_validator import validate_evidence, validate_quote
from tests.ai.fake_llm import FakeClient, cand, terms

SEG = Segment(
    3,
    1,
    "2.2 Renewal",
    "This Agreement shall automatically renew unless either party provides written notice of "
    'non-renewal at least ninety (90) days before the expiration of the "then-current" term.',
)


def test_exact_quote_is_verified_with_offsets():
    quote = "at least ninety (90) days before the expiration"
    c = validate_quote(quote, SEG)
    assert c.validation_status == "verified"
    assert SEG.text[c.char_start : c.char_end] == quote
    assert c.segment_seq == 3 and c.source_text == quote


def test_whitespace_case_and_curly_quotes_are_verified():
    quote = "AT LEAST  ninety (90)\n days before the expiration of the “then-current” term"
    c = validate_quote(quote, SEG)
    assert c.validation_status == "verified"
    assert SEG.text[c.char_start : c.char_end].lower() == (
        'at least ninety (90) days before the expiration of the "then-current" term'
    )


def test_one_typo_is_approximate():
    c = validate_quote("at least ninetv (90) days before the expiration", SEG)
    assert c.validation_status == "approximate"
    assert c.char_start is not None and c.char_end > c.char_start
    assert "ninety (90) days" in SEG.text[c.char_start : c.char_end]


def test_invented_quote_is_not_found():
    c = validate_quote("Customer shall pay a late fee of five percent per month", SEG)
    assert c.validation_status == "not_found"
    assert c.char_start is None and c.char_end is None


def test_unknown_segment_label_is_discarded():
    window = {3: SEG}
    evidence = [
        {"segment_id": "S9", "quote": "ninety (90) days"},
        {"segment_id": "S3", "quote": "ninety (90) days"},
    ]
    citations = validate_evidence(evidence, window)
    assert [c.segment_seq for c in citations] == [3]


NOTICE = {
    "value": 90,
    "unit": "days",
    "anchor": "expiration_date",
    "purpose": "non_renewal",
}


def test_invented_quote_forces_low_confidence_in_pipeline():
    client = FakeClient(
        # Quote is invented (not in the document) but consistent with the value.
        terms=[terms(notice_period=[cand(NOTICE, "S3", "ninety days notice before expiry")])]
    )
    result = analyze([SEG], client=client)
    (item,) = result.items
    assert item.confidence == "low"
    assert item.citations[0].validation_status == "not_found"
    assert result.stats["citations_not_found"] == 1


def test_approximate_caps_confidence_at_medium():
    quote = "at least ninetv (90) days before the expiration"
    client = FakeClient(terms=[terms(notice_period=[cand(NOTICE, "S3", quote)])])
    (item,) = analyze([SEG], client=client).items
    assert item.confidence == "medium"


def test_candidate_without_valid_evidence_is_dropped():
    client = FakeClient(terms=[terms(notice_period=[cand(NOTICE, "S42", "ninety (90) days")])])
    result = analyze([SEG], client=client)
    assert result.items == []
    assert result.stats["dropped_unsupported"] == 1
