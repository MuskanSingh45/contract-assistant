"""Schema validation and business rules for model candidates (docs/ai/pipeline.md §4)."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Any

from dateutil import parser as date_parser
from jsonschema import Draft202012Validator

DATE_FIELDS = ("effective_date", "expiration_date")
DATE_MISMATCH_NOTE = "Model date does not match quoted text"

# Two different defaults: a component that is missing from the text shows up as a difference.
_DEFAULT_A = datetime(2000, 1, 1, tzinfo=UTC)
_DEFAULT_B = datetime(2001, 2, 2, tzinfo=UTC)


def schema_error(data: Any, schema: dict[str, Any]) -> str | None:
    """Return a short description of the first schema violation, or None if valid."""
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if not errors:
        return None
    err = errors[0]
    path = "/".join(str(p) for p in err.path) or "(root)"
    return f"at {path}: {err.message[:300]}"


def parse_iso_date(value: str | None) -> date | None:
    """Parse YYYY-MM-DD into a real calendar date; None if absent or invalid."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_date_text(text: str) -> date | None:
    """Parse quoted date text (non-fuzzy). None if unparseable or day/month/year is missing."""
    try:
        a = date_parser.parse(text, fuzzy=False, default=_DEFAULT_A)
        b = date_parser.parse(text, fuzzy=False, default=_DEFAULT_B)
    except (ValueError, OverflowError, TypeError):
        return None
    if (a.year, a.month, a.day) != (b.year, b.month, b.day):
        return None
    return a.date()


def _positive(value: Any, nullable: bool = False) -> bool:
    if value is None:
        return nullable
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def check_term_value(field: str, value: dict[str, Any]) -> tuple[bool, str | None, str | None]:
    """Business-validate one terms candidate value (may normalize `value` in place).

    Returns (keep, confidence_cap, note_to_append). confidence_cap is None for no cap.
    """
    if field in DATE_FIELDS:
        raw = value.get("date")
        parsed_model = parse_iso_date(raw)
        if raw is not None and parsed_model is None:
            return False, None, None
        parsed_text = parse_date_text(value.get("date_text", ""))
        if parsed_text is None or parsed_model is None:
            return True, "medium", None
        if parsed_text != parsed_model:
            return True, "low", DATE_MISMATCH_NOTE
        return True, None, None
    if field == "party" and isinstance(value.get("role"), str):
        # Small models sometimes emit enum-style roles ("service_provider").
        value["role"] = value["role"].replace("_", " ").strip() or None
        return True, None, None
    if field == "initial_term":
        return _positive(value.get("value")), None, None
    if field == "renewal_terms":
        return _positive(value.get("period_value"), nullable=True), None, None
    if field == "notice_period":
        return _positive(value.get("value")), None, None
    return True, None, None


def check_obligation_value(value: dict[str, Any]) -> bool:
    offset = (value.get("due_rule") or {}).get("offset_days")
    return isinstance(offset, int) and not isinstance(offset, bool) and offset >= 0


_RENEWAL_CONTEXT = re.compile(r"expir|renew|end of|\bterm\b", re.IGNORECASE)
_ONES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_TENS = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_OBLIGATION_VERB = re.compile(r"\b(shall|must|will|agrees?|is required|are required|undertakes?)\b", re.IGNORECASE)
_PERMISSION = re.compile(r"\bmay\b", re.IGNORECASE)


def number_words(n: int) -> set[str]:
    """Ways a contract may write n: '90', 'ninety', 'ninety-nine' / 'ninety nine' (1-199)."""
    forms = {str(n)}
    if 0 <= n < 20:
        forms.add(_ONES[n])
    elif 20 <= n < 100:
        tens, ones = divmod(n, 10)
        word = _TENS[tens - 2]
        forms |= {word} if ones == 0 else {f"{word}-{_ONES[ones]}", f"{word} {_ONES[ones]}"}
    elif 100 <= n < 200:
        forms |= (
            {f"one hundred {w}".strip() for w in number_words(n - 100) - {str(n - 100)}} if n > 100 else {"one hundred"}
        )
    return forms


def number_and_unit_in_text(value: Any, unit: str, text: str) -> bool:
    """The cited text must contain both the number (digits or words) and the unit stem."""
    if not isinstance(value, int) or isinstance(value, bool):
        return False
    stem = {
        "business_days": "day",
        "days": "day",
        "months": "month",
        "years": "year",
    }.get(unit, unit.rstrip("s"))
    has_number = any(re.search(rf"(?<![\w-]){re.escape(f)}(?![\w-])", text) for f in number_words(value))
    return has_number and stem in text


def is_permission_only(quotes: list[str]) -> bool:
    """'Customer may inspect ...' grants a right; it is not an obligation."""
    text = " ".join(quotes)
    return bool(_PERMISSION.search(text)) and not _OBLIGATION_VERB.search(text)


ANCHOR_NOTE = "Quoted text does not tie this notice to expiration or renewal"


def check_value_against_citations(
    field: str, value: dict[str, Any], contexts: list[str]
) -> tuple[bool, dict[str, Any], str | None]:
    """Guard against values the cited text does not support (small models over-infer these).
    `contexts` = each citation's matched span with surrounding text (or the quote if not found).

    - initial_term: the cited text must mention the unit (year/month/day); a length computed from
      start/end dates is dropped.
    - notice_period: the cited text must contain the number (digits or words) and the unit, else dropped.
    - renewal_terms: an unsupported period is cleared (type kept) with a note.
    - notice_period anchored to expiration/renewal: the cited text must mention expiry/renewal/term,
      otherwise the anchor becomes "other" with a note.
    Returns (keep, value, note_to_append).
    """
    text = " ".join(contexts).lower()
    if field == "initial_term":
        unit = str(value.get("unit", "")).rstrip("s")
        return (bool(unit) and unit in text), value, None
    if field == "notice_period" and not number_and_unit_in_text(value.get("value"), str(value.get("unit", "")), text):
        return False, value, None  # e.g. "every two weeks" read as a 2-day notice
    if (
        field == "renewal_terms"
        and value.get("period_value") is not None
        and not number_and_unit_in_text(value["period_value"], str(value.get("period_unit") or ""), text)
    ):
        return (
            True,
            {**value, "period_value": None, "period_unit": None},
            "Renewal period not found in quoted text",
        )
    renewal_anchor = value.get("anchor") in ("expiration_date", "renewal_date")
    if field == "notice_period" and renewal_anchor and not _RENEWAL_CONTEXT.search(text):
        return True, {**value, "anchor": "other"}, ANCHOR_NOTE
    return True, value, None
