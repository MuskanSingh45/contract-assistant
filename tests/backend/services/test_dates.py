from datetime import date

from backend.utils.dates import (
    BUSINESS_DAYS_NOTE,
    RenewalInputs,
    add_period,
    calculate_renewal,
    days_until,
    lifecycle_status,
    obligation_due_date,
    parse_date_text,
    subtract_period,
)

TODAY = date(2026, 10, 3)


def _due(basis, frequency, offset=0, **kw):
    params = {
        "due_rule": {"basis": basis, "offset_days": offset},
        "frequency": frequency,
        "due_date_text": None,
        "effective_date": None,
        "notice_deadline": None,
        "today": TODAY,
    }
    params.update(kw)
    return obligation_due_date(**params)


# 1. Acme
def test_acme_notice_deadline():
    r = calculate_renewal(
        RenewalInputs(
            expiration_date=date(2027, 1, 31),
            renewal_type="automatic",
            renewal_period=(12, "months"),
            notice_period=(90, "days", "expiration_date"),
        ),
        TODAY,
    )
    assert r.expiration_source == "explicit"
    assert r.current_term_end == date(2027, 1, 31)
    assert r.notice_deadline == date(2026, 11, 2)
    assert r.calculation_status == "calculated"
    assert r.calculation_note is None
    assert lifecycle_status(r.current_term_end, r.notice_deadline, TODAY) == "expiring_soon"
    assert days_until(r.notice_deadline, TODAY) == 30


# 2. Month clamp
def test_months_clamp():
    assert subtract_period(date(2027, 3, 31), 1, "months") == date(2027, 2, 28)
    assert add_period(date(2027, 1, 31), 1, "months") == date(2027, 2, 28)


# 3. Business days
def test_business_days():
    assert subtract_period(date(2026, 11, 16), 10, "business_days") == date(2026, 11, 2)


def test_business_days_note():
    r = calculate_renewal(
        RenewalInputs(
            expiration_date=date(2026, 11, 16),
            notice_period=(10, "business_days", "expiration_date"),
        ),
        TODAY,
    )
    assert r.notice_deadline == date(2026, 11, 2)
    assert BUSINESS_DAYS_NOTE in r.calculation_note
    assert r.calculation_status == "calculated"


# 4. Roll-forward
def test_roll_forward():
    r = calculate_renewal(
        RenewalInputs(
            expiration_date=date(2026, 1, 31),
            renewal_type="automatic",
            renewal_period=(12, "months"),
            notice_period=(90, "days", "renewal_date"),
        ),
        TODAY,
    )
    assert r.expiration_date == date(2026, 1, 31)
    assert r.current_term_end == date(2027, 1, 31)
    assert r.notice_deadline == date(2026, 11, 2)


def test_roll_forward_no_month_end_drift():
    r = calculate_renewal(
        RenewalInputs(
            expiration_date=date(2026, 1, 31),
            renewal_type="automatic",
            renewal_period=(1, "months"),
        ),
        TODAY,
    )
    assert r.current_term_end == date(2026, 10, 31)


# 5. Not automatic and expired
def test_not_automatic_expired():
    r = calculate_renewal(
        RenewalInputs(expiration_date=date(2026, 1, 31), renewal_type="none"),
        TODAY,
    )
    assert r.current_term_end == date(2026, 1, 31)
    assert lifecycle_status(r.current_term_end, r.notice_deadline, TODAY) == "expired"


# 6. Calculated expiration
def test_calculated_expiration():
    r = calculate_renewal(
        RenewalInputs(effective_date=date(2025, 1, 31), initial_term=(2, "years")),
        TODAY,
    )
    assert r.expiration_date == date(2027, 1, 31)
    assert r.expiration_source == "calculated"
    assert r.calculation_status == "calculated"
    assert r.calculation_note == "No notice period found"


# 7. Explicit expiration != effective + term
def test_expiration_conflict():
    r = calculate_renewal(
        RenewalInputs(
            effective_date=date(2025, 1, 31),
            initial_term=(2, "years"),
            expiration_date=date(2027, 6, 30),
            notice_period=(90, "days", "expiration_date"),
        ),
        TODAY,
    )
    assert r.expiration_conflict is True
    assert r.calculation_status == "blocked_by_conflict"
    assert r.expiration_date is None
    assert r.current_term_end is None
    assert r.notice_deadline is None


def test_explicit_matching_calculated_is_not_conflict():
    r = calculate_renewal(
        RenewalInputs(
            effective_date=date(2025, 1, 31),
            initial_term=(2, "years"),
            expiration_date=date(2027, 1, 31),
        ),
        TODAY,
    )
    assert r.expiration_conflict is False
    assert r.expiration_source == "explicit"


def test_conflicted_expiration_field():
    r = calculate_renewal(
        RenewalInputs(
            expiration_date=date(2027, 1, 31),
            notice_period=(90, "days", "expiration_date"),
            conflicted_fields=frozenset({"expiration_date"}),
        ),
        TODAY,
    )
    assert r.calculation_status == "blocked_by_conflict"
    assert r.expiration_date is None
    assert r.notice_deadline is None


# 8. Conflicting notice periods
def test_notice_conflict():
    r = calculate_renewal(
        RenewalInputs(
            expiration_date=date(2026, 12, 31),
            notice_period=None,
            conflicted_fields=frozenset({"notice_period"}),
        ),
        TODAY,
    )
    assert r.calculation_status == "blocked_by_conflict"
    assert r.notice_deadline is None
    assert r.current_term_end == date(2026, 12, 31)
    assert "notice period" in r.calculation_note


def test_renewal_terms_conflict():
    r = calculate_renewal(
        RenewalInputs(
            expiration_date=date(2026, 1, 31),
            renewal_type="automatic",
            renewal_period=(12, "months"),
            conflicted_fields=frozenset({"renewal_terms"}),
        ),
        TODAY,
    )
    assert r.calculation_status == "blocked_by_conflict"
    assert r.current_term_end is None


# Globex (clarification case 1 values)
def test_globex_deadline_passed():
    r = calculate_renewal(
        RenewalInputs(
            expiration_date=date(2026, 12, 31),
            notice_period=(90, "days", "expiration_date"),
        ),
        TODAY,
    )
    assert r.notice_deadline == date(2026, 10, 2)
    assert days_until(r.notice_deadline, TODAY) == -1
    assert subtract_period(date(2026, 12, 31), 60, "days") == date(2026, 11, 1)


# 11. Obligation due dates
def test_quarterly_period_end():
    assert _due("calendar_period_end", "quarterly", 30) == (
        date(2026, 10, 30),
        "calculated",
    )


def test_monthly_period_end_rolls_to_next_when_passed():
    # Sept ends 2026-09-30, +1 = 2026-10-01 < today -> Oct end 2026-10-31 + 1.
    assert _due("calendar_period_end", "monthly", 1) == (
        date(2026, 11, 1),
        "calculated",
    )


def test_annual_anniversary():
    assert _due("effective_date_anniversary", "annually", effective_date=date(2025, 1, 31)) == (
        date(2027, 1, 31),
        "calculated",
    )


def test_renewal_notice_deadline_basis():
    assert _due("renewal_notice_deadline", "one_time", notice_deadline=date(2026, 11, 2)) == (
        date(2026, 11, 2),
        "calculated",
    )
    assert _due("renewal_notice_deadline", "one_time") == (None, None)


def test_explicit_and_null_bases():
    assert _due("explicit_date", "one_time", due_date_text="March 1, 2027") == (
        date(2027, 3, 1),
        "explicit",
    )
    assert _due("explicit_date", "other", due_date_text="first business day") == (
        None,
        None,
    )
    assert _due("unspecified", "monthly") == (None, None)
    assert _due("calendar_period_end", "one_time", 30) == (None, None)
    assert _due("effective_date_anniversary", "other", effective_date=date(2025, 1, 31)) == (
        None,
        None,
    )
    assert obligation_due_date(
        due_rule=None,
        frequency=None,
        due_date_text=None,
        effective_date=None,
        notice_deadline=None,
        today=TODAY,
    ) == (None, None)


# 12. anchor other
def test_anchor_other_incomplete():
    r = calculate_renewal(
        RenewalInputs(
            expiration_date=date(2027, 1, 31),
            notice_period=(30, "days", "other"),
        ),
        TODAY,
    )
    assert r.calculation_status == "incomplete"
    assert r.notice_deadline is None
    assert r.calculation_note == "Notice period is not anchored to the expiration date"


def test_no_expiration_incomplete():
    r = calculate_renewal(RenewalInputs(effective_date=date(2025, 1, 31)), TODAY)
    assert r.calculation_status == "incomplete"
    assert r.expiration_date is None
    assert "No expiration date or initial term found" in r.calculation_note
    assert lifecycle_status(r.current_term_end, r.notice_deadline, TODAY) == "unknown"


def test_lifecycle_active():
    assert lifecycle_status(date(2027, 12, 31), date(2027, 10, 1), TODAY) == "active"
    assert lifecycle_status(date(2026, 11, 1), None, TODAY) == "expiring_soon"


def test_parse_date_text():
    assert parse_date_text("January 31, 2025") == date(2025, 1, 31)
    assert parse_date_text("2027-01-31") == date(2027, 1, 31)
    assert parse_date_text("January 2025") is None
    assert parse_date_text("2025") is None
    assert parse_date_text("January 31") is None
    assert parse_date_text("the first business day of the year") is None
    assert parse_date_text(None) is None
    assert days_until(None, TODAY) is None
