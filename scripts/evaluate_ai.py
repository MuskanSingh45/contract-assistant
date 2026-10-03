"""Evaluate the AI pipeline against contracts/fixtures/expected-extractions/*.json.

Runs each sample through the SAME path the app uses: parse -> ai pipeline -> persist into a
temporary SQLite DB -> deterministic date calculation (with the fixture's evaluation_date as
"today"). Then it scores the results. Needs Ollama running (about 2 minutes per sample on an M1 Pro).

    .venv/bin/python scripts/evaluate_ai.py                      # all samples
    .venv/bin/python scripts/evaluate_ai.py acme-services-agreement
    .venv/bin/python scripts/evaluate_ai.py --rescore ai/evaluation/results/<file>.json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai.evaluation.evaluator import RESULTS, evaluate, load_fixtures
from ai.pipeline.orchestrator import analyze
from backend.documents.parser import TEXT_MIME, parse_document
from backend.services import analysis_service, calculation_service, common
from db.database import connect, migrate


def collect(sample_path: Path, today: date) -> dict:
    """Run one sample end to end and return its observable outputs."""
    calculation_service.today = common.today = lambda: today  # freeze "today" for date maths
    conn = connect(Path(tempfile.mkdtemp()) / "eval.db")
    migrate(conn)
    now = common.utc_now()
    conn.execute(
        "INSERT INTO contracts (id, name, created_at, updated_at) VALUES ('ctr_eval', 'eval', ?, ?)",
        (now, now),
    )
    conn.execute(
        """INSERT INTO contract_versions (id, contract_id, version_number, file_name, file_path, file_hash, mime_type,
               uploaded_at) VALUES ('ver_eval', 'ctr_eval', 1, ?, ?, 'eval', ?, ?)""",
        (sample_path.name, str(sample_path), TEXT_MIME, now),
    )
    conn.commit()

    segments, pages = parse_document(str(sample_path), TEXT_MIME)
    started = time.monotonic()
    result = analyze(segments)
    seconds = round(time.monotonic() - started, 1)
    version = conn.execute("SELECT * FROM contract_versions WHERE id = 'ver_eval'").fetchone()
    analysis_service._persist(conn, version, segments, pages, result)

    def statuses(entity_type: str, entity_id: str) -> list[str]:
        return [
            r[0]
            for r in conn.execute(
                "SELECT validation_status FROM citations WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            )
        ]

    items = [
        {
            "field_name": r["field_name"],
            "value": json.loads(r["value_json"]),
            "confidence": r["confidence"],
            "ambiguity_note": r["ambiguity_note"],
            "citation_statuses": statuses("extracted_item", r["id"]),
        }
        for r in conn.execute("SELECT * FROM extracted_items WHERE contract_version_id = 'ver_eval'")
    ]
    obligations = [
        {
            "description": r["description"],
            "responsible_party": r["responsible_party"],
            "frequency": r["frequency"],
            "due_rule": json.loads(r["due_rule_json"] or "null"),
            "due_date": r["due_date"],
            "confidence": r["confidence"],
            "citation_statuses": statuses("obligation", r["id"]),
        }
        for r in conn.execute("SELECT * FROM obligations WHERE contract_version_id = 'ver_eval'")
    ]
    clarifications = [
        {"kind": r["kind"], "field_name": r["field_name"], "question": r["question"]}
        for r in conn.execute("SELECT * FROM clarification_questions WHERE contract_version_id = 'ver_eval'")
    ]
    renewal = dict(conn.execute("SELECT * FROM renewals WHERE contract_version_id = 'ver_eval'").fetchone() or {})
    conn.close()
    return {
        "items": items,
        "obligations": obligations,
        "clarifications": clarifications,
        "renewal": renewal,
        "stats": {**result.stats, "seconds": seconds},
        "model": result.model_name,
        "prompt_version": result.prompt_version,
    }


def print_report(report: dict, actual: dict) -> None:
    print("\n" + "=" * 78)
    for name, s in report["samples"].items():
        stats = actual[name]["stats"]
        print(f"\n## {name}  ({stats.get('seconds')}s, retries={stats.get('retries', 0)})")
        for field, r in s["fields"].items():
            flag = "ok " if not r["missing"] and not r["hallucinated"] else "ERR"
            extra = ""
            if r["missing"]:
                extra += f" missing={r['missing']}"
            if r["hallucinated"]:
                extra += f" unexpected={r['hallucinated']}"
            print(f"  [{flag}] {field:<18} found {r['found']}/{r['expected_required']}{extra}")
        ob = s["obligations"]
        print(
            f"  obligations: found {ob['found']}/{ob['expected_required']}"
            f"{' missing=' + str(ob['missing']) if ob['missing'] else ''}"
        )
        for e in ob["attribute_errors"]:
            print(
                f"    attr mismatch: {e['obligation']!r} {e['attribute']}: expected {e['expected']}, got {e['actual']}"
            )
        if ob["rights_as_obligations"]:
            print(f"    RIGHTS EXTRACTED AS OBLIGATIONS: {ob['rights_as_obligations']}")
        if ob["unexpected"]:
            print(f"    extra (not in fixture): {ob['unexpected']}")
        print(
            f"  conflicts: expected {s['conflicts']['expected']} actual {s['conflicts']['actual']}"
            f" {'ok' if s['conflicts']['ok'] else 'ERR'}; clarifications {'ok' if s['clarifications_ok'] else 'ERR'}"
        )
        print(
            f"  dates: renewal {'ok' if not s['renewal_errors'] else s['renewal_errors']};"
            f" due {'ok' if not s['due_date_errors'] else s['due_date_errors']}"
        )
        print(f"  citations: {s['citations']}")
    print("\n## SUMMARY")
    for k, v in report["summary"].items():
        print(f"  {k:<36} {v}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("samples", nargs="*", help="fixture names (default: all)")
    parser.add_argument(
        "--rescore",
        type=Path,
        help="re-score a saved results file without calling the model",
    )
    args = parser.parse_args()

    if args.rescore:
        saved = json.loads(args.rescore.read_text())
        actual = saved["actual"]
        fixtures = load_fixtures(list(actual))
    else:
        fixtures = load_fixtures(args.samples or None)
        actual = {}
        for name, fx in fixtures.items():
            print(f"running {name} ...", flush=True)
            actual[name] = collect(
                ROOT / "contracts" / fx["sample"],
                date.fromisoformat(fx["evaluation_date"]),
            )

    report = evaluate(fixtures, actual)
    print_report(report, actual)
    if not args.rescore:
        RESULTS.mkdir(exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        out = RESULTS / f"{stamp}.json"
        meta = next(iter(actual.values()), {})
        out.write_text(
            json.dumps(
                {
                    "model": meta.get("model"),
                    "prompt_version": meta.get("prompt_version"),
                    "summary": report["summary"],
                    "report": report,
                    "actual": actual,
                },
                indent=2,
                default=str,
            )
        )
        print(f"\nsaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
