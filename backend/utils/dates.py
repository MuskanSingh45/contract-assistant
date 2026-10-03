"""Deterministic date calculation (docs/architecture/date-calculation.md).

Pure functions only: no I/O, no LLM. ``today`` is always passed in.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

UPCOMING_WINDOW_DAYS = 60

BUSINESS_DAYS_NOTE = "Business days exclude weekends only; public holidays are not considered."

_FREQUENCY_MONTHS = {"monthly": 1, "quarterly": 3, "annually": 12}

_EXPIRATION_INPUTS = ("effective_date", "expiration_date", "initial_term")


@dataclass
class RenewalInputs:
    effective_date: date | None = None
    expiration_date: date | None = None
    initial_term: tuple[int, str] | None = None
    renewal_type: str | None = None
    renewal_period: tuple[int, str] | None = None
    notice_period: tuple[int, str, str] | None = None
    conflicted_fields: frozenset[str] = frozenset()


@dataclass
class RenewalResult:
    effective_date: date | None
    expiration_date: date | None
    expiration_source: str | None
    renewal_type: str | None
    renewal_period_value: int | None
    renewal_period_unit: str | None
    current_term_end: date | None
    notice_period_value: int | None
    notice_period_unit: str | None
    notice_anchor: str | None
    notice_deadline: date | None
    calculation_status: str
    calculation_note: str | None
    expiration_conflict: bool = False


def add_period(d: date, value: int, unit: str) -> date:
    if unit == "days":
        return d + timedelta(days=value)
    if unit == "months":
        return d + relativedelta(months=value)
    if unit == "years":
        return d + relativedelta(years=value)
    raise ValueError(f"Unsupported period unit: {unit}")


def subtract_period(d: date, value: int, unit: str) -> date:
    if unit == "business_days":
        result = d
        remaining = value
        while remaining > 0:
            result -= timedelta(days=1)
            if result.weekday() < 5:
                remaining -= 1
        return result
    return add_period(d, -value, unit)


def _roll_forward(expiration: date, value: int, unit: str, today: date) -> date:
    k = 1
    while True:
        candidate = add_period(expiration, value * k, unit)
        if candidate >= today:
            return candidate
        k += 1


def _conflict_note(fields: list[str], what: str) -> str:
    names = ", ".join(f.replace("_", " ") for f in fields)
    return f"Conflicting {names} candidates; resolve the clarification question to calculate {what}."


def calculate_renewal(inputs: RenewalInputs, today: date) -> RenewalResult:
    conflicted = inputs.conflicted_fields
    notes: list[str] = []
    blocked = False
    incomplete = False
    expiration_conflict = False

    # Expiration date (spec §2).
    expiration: date | None = None
    expiration_source: str | None = None
    exp_conflicts = [f for f in _EXPIRATION_INPUTS if f in conflicted]
    if exp_conflicts:
        blocked = True
        notes.append(_conflict_note(exp_conflicts, "the expiration date"))
    else:
        calculated = None
        if inputs.effective_date is not None and inputs.initial_term is not None:
            calculated = add_period(inputs.effective_date, *inputs.initial_term)
        explicit = inputs.expiration_date
        if explicit is not None and calculated is not None and explicit != calculated:
            blocked = True
            expiration_conflict = True
            notes.append(
                f"Explicit expiration date {explicit.isoformat()} does not match effective date "
                f"plus initial term ({calculated.isoformat()}); resolve the clarification "
                "question to calculate the expiration date."
            )
        elif explicit is not None:
            expiration, expiration_source = explicit, "explicit"
        elif calculated is not None:
            expiration, expiration_source = calculated, "calculated"
        else:
            incomplete = True
            notes.append("No expiration date or initial term found")

    # Current term end (spec §3).
    renewal_conflict = "renewal_terms" in conflicted
    renewal_type = None if renewal_conflict else inputs.renewal_type
    renewal_period = None if renewal_conflict else inputs.renewal_period
    current_term_end: date | None = None
    if renewal_conflict:
        blocked = True
        notes.append(_conflict_note(["renewal_terms"], "the current term end"))
        if expiration is not None and expiration >= today:
            current_term_end = expiration
    elif expiration is not None:
        if renewal_type == "automatic" and renewal_period is not None and expiration < today:
            current_term_end = _roll_forward(expiration, *renewal_period, today)
        else:
            current_term_end = expiration

    # Notice deadline (spec §4).
    notice = None if "notice_period" in conflicted else inputs.notice_period
    notice_deadline: date | None = None
    if "notice_period" in conflicted:
        blocked = True
        notes.append(_conflict_note(["notice_period"], "the notice deadline"))
    elif notice is None:
        notes.append("No notice period found")
    else:
        value, unit, anchor = notice
        if anchor not in ("expiration_date", "renewal_date"):
            incomplete = True
            notes.append("Notice period is not anchored to the expiration date")
        elif current_term_end is not None:
            notice_deadline = subtract_period(current_term_end, value, unit)
            if unit == "business_days":
                notes.append(BUSINESS_DAYS_NOTE)

    if blocked:
        status = "blocked_by_conflict"
    elif incomplete:
        status = "incomplete"
    else:
        status = "calculated"

    return RenewalResult(
        effective_date=None if "effective_date" in conflicted else inputs.effective_date,
        expiration_date=expiration,
        expiration_source=expiration_source,
        renewal_type=renewal_type,
        renewal_period_value=renewal_period[0] if renewal_period else None,
        renewal_period_unit=renewal_period[1] if renewal_period else None,
        current_term_end=current_term_end,
        notice_period_value=notice[0] if notice else None,
        notice_period_unit=notice[1] if notice else None,
        notice_anchor=notice[2] if notice else None,
        notice_deadline=notice_deadline,
        calculation_status=status,
        calculation_note=" ".join(notes) or None,
        expiration_conflict=expiration_conflict,
    )


def lifecycle_status(
    current_term_end: date | None,
    notice_deadline: date | None,
    today: date,
    window_days: int = UPCOMING_WINDOW_DAYS,
) -> str:
    if current_term_end is None:
        return "unknown"
    if current_term_end < today:
        return "expired"
    target = notice_deadline if notice_deadline is not None else current_term_end
    if today <= target <= today + timedelta(days=window_days):
        return "expiring_soon"
    return "active"


def days_until(d: date | None, today: date) -> int | None:
    if d is None:
        return None
    return (d - today).days


def _period_end(d: date, months: int) -> date:
    """Last day of the calendar month/quarter/year containing ``d``."""
    start_month = ((d.month - 1) // months) * months + 1
    start = date(d.year, start_month, 1)
    return start + relativedelta(months=months) - timedelta(days=1)


def obligation_due_date(
    *,
    due_rule: dict | None,
    frequency: str | None,
    due_date_text: str | None,
    effective_date: date | None,
    notice_deadline: date | None,
    today: date,
) -> tuple[date | None, str | None]:
    basis = (due_rule or {}).get("basis")
    offset = timedelta(days=(due_rule or {}).get("offset_days") or 0)

    if basis == "explicit_date":
        parsed = parse_date_text(due_date_text)
        return (parsed, "explicit") if parsed is not None else (None, None)

    if basis == "renewal_notice_deadline":
        return (notice_deadline, "calculated") if notice_deadline is not None else (None, None)

    months = _FREQUENCY_MONTHS.get(frequency or "")
    if months is None:
        return None, None

    if basis == "effective_date_anniversary":
        if effective_date is None:
            return None, None
        k = 1
        while True:
            candidate = effective_date + relativedelta(months=months * k) + offset
            if candidate >= today:
                return candidate, "calculated"
            k += 1

    if basis == "calendar_period_end":
        end = _period_end(today, months)
        if end > today:
            end = _period_end(end - relativedelta(months=months), months)
        due = end + offset
        if due < today:
            due = _period_end(end + timedelta(days=1), months) + offset
        return due, "calculated"

    return None, None


_SENTINEL_A = datetime(1, 1, 1, tzinfo=UTC)
_SENTINEL_B = datetime(2, 2, 2, tzinfo=UTC)


def parse_date_text(text: str | None) -> date | None:
    """Parse a full date from quoted text; None if unparseable or missing day/month/year."""
    if not text or not text.strip():
        return None
    try:
        a = date_parser.parse(text, fuzzy=False, default=_SENTINEL_A)
        b = date_parser.parse(text, fuzzy=False, default=_SENTINEL_B)
    except (ValueError, OverflowError):
        return None
    if a.date() != b.date():
        return None
    return a.date()
