"""Pure comparison helpers for AI evaluation. Fixture format: contracts/README.md."""

from __future__ import annotations

import re
from typing import Any

_CONTROL_KEYS = {"optional", "summary_contains"}
_SUFFIX = re.compile(r"\b(inc|ltd|llc|corp|corporation|limited|co)\b\.?$")


def norm_name(name: str | None) -> str:
    """'Example Services Ltd.' -> 'example services' (for party / responsible-party matching)."""
    text = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    text = re.sub(r"\s+", " ", text).strip()
    return _SUFFIX.sub("", text).strip()


def contains_all(text: str | None, terms: list[str]) -> bool:
    low = (text or "").lower()
    return all(t.lower() in low for t in terms)


def value_matches(field: str, expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """Every non-control key in `expected` must equal the actual value (names compared normalized)."""
    if "summary_contains" in expected and not contains_all(actual.get("summary"), expected["summary_contains"]):
        return False
    for key, want in expected.items():
        if key in _CONTROL_KEYS:
            continue
        got = actual.get(key)
        if field == "party" and key == "name":
            if norm_name(got) != norm_name(want):
                return False
        elif field == "party" and key == "role":
            if (got or "").lower().replace("_", " ") != (want or "").lower():
                return False
        elif got != want:
            return False
    return True


def match_field(field: str, expected: list[dict], actual: list[dict]) -> dict[str, Any]:
    """Greedy one-to-one matching of expected candidates to extracted values for one field."""
    unmatched = list(range(len(actual)))
    found, missing = 0, []
    for exp in expected:
        hit = next((i for i in unmatched if value_matches(field, exp, actual[i])), None)
        if hit is not None:
            unmatched.remove(hit)
            found += 1
        elif not exp.get("optional"):
            missing.append(exp)
    required = sum(1 for e in expected if not e.get("optional"))
    return {
        "expected_required": required,
        "found": found,
        "missing": missing,
        "hallucinated": [actual[i] for i in unmatched],
        "expected_empty": not expected,
        "correct_empty": not expected and not actual,
    }


def _attribute_ok(key: str, want: Any, got: dict[str, Any]) -> bool:
    if key == "responsible_party":
        return norm_name(got.get("responsible_party")) == norm_name(want)
    if key == "due_rule":
        return all((got.get("due_rule") or {}).get(k) == v for k, v in want.items())
    return got.get(key) == want


def match_obligations(expected: list[dict], actual: list[dict], must_not: list[str]) -> dict[str, Any]:
    unmatched = list(range(len(actual)))
    found, missing, attr_checks, attr_errors = 0, [], 0, []
    for exp in expected:
        hit = next(
            (i for i in unmatched if contains_all(actual[i]["description"], exp["description_contains"])),
            None,
        )
        if hit is None:
            if not exp.get("optional"):
                missing.append(exp["description_contains"])
            continue
        unmatched.remove(hit)
        if exp.get("optional"):
            continue
        found += 1
        got = actual[hit]
        for key in ("responsible_party", "frequency", "due_rule"):
            if key in exp:
                attr_checks += 1
                if not _attribute_ok(key, exp[key], got):
                    attr_errors.append(
                        {
                            "obligation": got["description"],
                            "attribute": key,
                            "expected": exp[key],
                            "actual": got.get(key),
                        }
                    )
    rights = [a["description"] for a in actual if any(t.lower() in a["description"].lower() for t in must_not)]
    return {
        "expected_required": sum(1 for e in expected if not e.get("optional")),
        "found": found,
        "missing": missing,
        "unexpected": [actual[i]["description"] for i in unmatched],
        "attribute_checks": attr_checks,
        "attribute_errors": attr_errors,
        "rights_as_obligations": rights,
    }


def score_sample(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    """Compare one sample's actual pipeline output with its fixture."""
    fields = {
        f: match_field(f, exp, [i["value"] for i in actual["items"] if i["field_name"] == f])
        for f, exp in expected["fields"].items()
    }
    obligations = match_obligations(
        expected.get("obligations", []),
        actual["obligations"],
        expected.get("must_not_contain_obligations", []),
    )

    actual_conflicts = sorted(c["field_name"] or "" for c in actual["clarifications"] if c["kind"] == "conflict")
    expected_conflicts = sorted(c["field_name"] for c in expected.get("conflicts", []))
    actual_kinds = sorted(c["kind"] for c in actual["clarifications"])
    clar_ok = all(any(k == e["kind"] for k in actual_kinds) for e in expected.get("clarifications", []))

    renewal_errors = {
        k: {"expected": v, "actual": (actual["renewal"] or {}).get(k)}
        for k, v in expected.get("renewal", {}).items()
        if (actual["renewal"] or {}).get(k) != v
    }
    due_errors = {}
    for term, want in expected.get("obligation_due_dates", {}).items():
        match = next(
            (o for o in actual["obligations"] if term.lower() in o["description"].lower()),
            None,
        )
        got = match["due_date"] if match else None
        if got != want:
            due_errors[term] = {"expected": want, "actual": got}

    statuses = [c for i in actual["items"] + actual["obligations"] for c in i["citation_statuses"]]
    return {
        "fields": fields,
        "obligations": obligations,
        "conflicts": {
            "expected": expected_conflicts,
            "actual": actual_conflicts,
            "ok": expected_conflicts == actual_conflicts,
        },
        "clarifications_ok": clar_ok,
        "renewal_errors": renewal_errors,
        "due_date_errors": due_errors,
        "citations": {s: statuses.count(s) for s in ("verified", "approximate", "not_found")},
    }


def summarize(scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-sample scores into headline metrics."""
    found = sum(f["found"] for s in scores for f in s["fields"].values())
    required = sum(f["expected_required"] for s in scores for f in s["fields"].values())
    missing = sum(len(f["missing"]) for s in scores for f in s["fields"].values())
    halluc = sum(len(f["hallucinated"]) for s in scores for f in s["fields"].values())
    empty_expected = sum(1 for s in scores for r in s["fields"].values() if r["expected_empty"])
    empty_correct = sum(1 for s in scores for r in s["fields"].values() if r["correct_empty"])
    ob_found = sum(s["obligations"]["found"] for s in scores)
    ob_req = sum(s["obligations"]["expected_required"] for s in scores)
    attr_checks = sum(s["obligations"]["attribute_checks"] for s in scores)
    attr_err = sum(len(s["obligations"]["attribute_errors"]) for s in scores)
    cites = {k: sum(s["citations"][k] for s in scores) for k in ("verified", "approximate", "not_found")}
    total_cites = sum(cites.values()) or 1

    def pct(a: int, b: int) -> float | None:
        return round(100 * a / b, 1) if b else None

    return {
        "field_recall_pct": pct(found, found + missing) if required else None,
        "field_precision_pct": pct(found, found + halluc),
        "hallucinated_values": halluc,
        "missing_info_correct": f"{empty_correct}/{empty_expected}",
        "obligation_recall_pct": pct(ob_found, ob_req),
        "obligation_attribute_accuracy_pct": pct(attr_checks - attr_err, attr_checks),
        "rights_as_obligations": sum(len(s["obligations"]["rights_as_obligations"]) for s in scores),
        "conflict_detection_ok": f"{sum(s['conflicts']['ok'] for s in scores)}/{len(scores)}",
        "date_results_ok": f"{sum(not s['renewal_errors'] and not s['due_date_errors'] for s in scores)}/{len(scores)}",
        "citations_verified_pct": pct(cites["verified"], total_cites),
        "citations_not_found": cites["not_found"],
    }
