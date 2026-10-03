"""Runs analysis for one version: parse -> ai pipeline -> date calculation -> comparison -> persist.

Docs: docs/api/analysis.md, docs/architecture/data-flow.md. Results are written in ONE transaction
at the end, so a failed analysis persists nothing partial.
"""

from __future__ import annotations

import logging
import sqlite3
import time

from ai import errors as ai_errors
from ai.llm.ollama_client import check_available
from ai.pipeline import clarification as templates
from ai.pipeline.orchestrator import analyze
from ai.types import AnalysisResult, Citation, Segment
from backend.core.dependencies import open_db
from backend.core.exceptions import AppError
from backend.documents.parser import DocumentParseError, NoExtractableText, parse_document
from backend.services import calculation_service, version_service
from backend.services.common import dumps, get_version, new_id, utc_now, version_counts

log = logging.getLogger(__name__)

# In-memory progress for the running analysis (stage "extracting" only). Single process MVP.
_progress: dict[str, tuple[int, int]] = {}


def progress_for(version_id: str) -> tuple[int, int] | None:
    return _progress.get(version_id)


def ensure_ai_available() -> None:
    reachable, model_ok = check_available()
    if not reachable:
        raise AppError("AI_UNAVAILABLE", "Ollama is not reachable. Start it with `ollama serve`.", 503)
    if not model_ok:
        raise AppError("AI_UNAVAILABLE", "The configured model is not available in Ollama.", 503)


def start(conn: sqlite3.Connection, contract_id: str, version_id: str | None) -> sqlite3.Row:
    version = get_version(conn, contract_id, version_id)
    if version["analysis_status"] in ("queued", "processing"):
        raise AppError("ANALYSIS_IN_PROGRESS", "This version is already being analyzed.", 409)
    ensure_ai_available()
    conn.execute(
        """UPDATE contract_versions SET analysis_status = 'queued', analysis_stage = NULL,
               analysis_error_code = NULL, analysis_error_message = NULL,
               analysis_started_at = NULL, analysis_completed_at = NULL WHERE id = ?""",
        (version["id"],),
    )
    conn.commit()
    return version


def mark_interrupted(conn: sqlite3.Connection) -> None:
    """On startup: analyses left queued/processing by a previous process can never finish."""
    cur = conn.execute(
        """UPDATE contract_versions SET analysis_status = 'failed', analysis_error_code = 'ANALYSIS_FAILED',
               analysis_error_message = 'Interrupted by server restart', analysis_completed_at = ?
           WHERE analysis_status IN ('queued', 'processing')""",
        (utc_now(),),
    )
    conn.commit()
    if cur.rowcount:
        log.warning(
            "marked %d analysis run(s) interrupted by the restart as failed",
            cur.rowcount,
            extra={"event": "analysis.interrupted", "count": cur.rowcount},
        )


def _set_stage(conn: sqlite3.Connection, version_id: str, stage: str) -> None:
    conn.execute("UPDATE contract_versions SET analysis_stage = ? WHERE id = ?", (stage, version_id))
    conn.commit()


def run(version_id: str) -> None:
    """Background task entry point. Opens its own connection."""
    conn = open_db()
    started = time.monotonic()
    try:
        conn.execute(
            """UPDATE contract_versions SET analysis_status = 'processing', analysis_stage = 'parsing',
                   analysis_started_at = ? WHERE id = ?""",
            (utc_now(), version_id),
        )
        conn.commit()
        version = conn.execute("SELECT * FROM contract_versions WHERE id = ?", (version_id,)).fetchone()
        log.info(
            "analysis %s started (%s)",
            version_id,
            version["file_name"],
            extra={"event": "analysis.started", "version_id": version_id},
        )
        segments, page_count = parse_document(version["file_path"], version["mime_type"])
        log.info(
            "analysis %s parsed: %d segments, %s pages",
            version_id,
            len(segments),
            page_count,
            extra={
                "event": "analysis.parsed",
                "version_id": version_id,
                "segments": len(segments),
                "pages": page_count,
            },
        )

        current_stage = ["extracting"]

        def on_progress(stage: str, current: int, total: int) -> None:
            if stage != current_stage[0]:
                current_stage[0] = stage
            _set_stage(conn, version_id, stage)
            if stage == "extracting":
                _progress[version_id] = (current, total)

        _set_stage(conn, version_id, "extracting")
        result = analyze(segments, on_progress=on_progress)
        _progress.pop(version_id, None)
        _set_stage(conn, version_id, "analyzing")
        _persist(conn, version, segments, page_count, result)
        duration = time.monotonic() - started
        log.info(
            "analysis %s completed in %.1fs: %s",
            version_id,
            duration,
            result.stats,
            extra={
                "event": "analysis.completed",
                "version_id": version_id,
                "duration_s": round(duration, 2),
                "stats": result.stats,
            },
        )
    except Exception as exc:
        conn.rollback()
        _progress.pop(version_id, None)
        code, message = _classify(exc)
        fields = {
            "event": "analysis.failed",
            "version_id": version_id,
            "error_code": code,
            "duration_s": round(time.monotonic() - started, 2),
        }
        if code == "ANALYSIS_FAILED":
            log.exception("analysis %s failed", version_id, extra=fields)
        else:
            log.warning("analysis %s failed: %s %s", version_id, code, message, extra=fields)
        conn.execute(
            """UPDATE contract_versions SET analysis_status = 'failed', analysis_error_code = ?,
                   analysis_error_message = ?, analysis_completed_at = ? WHERE id = ?""",
            (code, message, utc_now(), version_id),
        )
        conn.commit()
    finally:
        conn.close()


def _classify(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, NoExtractableText):
        return "NO_EXTRACTABLE_TEXT", "No text could be extracted. Scanned documents (OCR) are not supported."
    if isinstance(exc, DocumentParseError):
        return "DOCUMENT_PARSE_FAILED", "The document could not be read. It may be corrupt or password-protected."
    if isinstance(exc, ai_errors.AIUnavailable):
        return "AI_UNAVAILABLE", "The AI model became unavailable during analysis."
    if isinstance(exc, ai_errors.AITimeout):
        return "AI_TIMEOUT", "The AI model took too long to respond."
    if isinstance(exc, ai_errors.InvalidAIOutput):
        return "INVALID_AI_OUTPUT", str(exc) or "Model output did not match the expected schema."
    return "ANALYSIS_FAILED", "Analysis failed unexpectedly."


# ---------------------------------------------------------------- persistence


def _clear_previous_output(conn: sqlite3.Connection, version_id: str) -> None:
    for table in (
        "citations",
        "clarification_questions",
        "extracted_items",
        "obligations",
        "renewals",
        "version_changes",
        "document_segments",
    ):
        conn.execute(f"DELETE FROM {table} WHERE contract_version_id = ?", (version_id,))


def _insert_citations(conn, version_id, entity_type, entity_id, citations: list[Citation], seg_ids, segs) -> None:
    for c in citations:
        segment = segs.get(c.segment_seq)
        conn.execute(
            """INSERT INTO citations (id, contract_version_id, entity_type, entity_id, segment_id, page, section,
                   source_text, char_start, char_end, validation_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                new_id("cit"),
                version_id,
                entity_type,
                entity_id,
                seg_ids.get(c.segment_seq),
                segment.page if segment else None,
                segment.section if segment else None,
                c.source_text,
                c.char_start,
                c.char_end,
                c.validation_status,
            ),
        )


def _insert_clarification(conn, version_id, kind, field_name, question, option_ids, citations, seg_ids, segs, now):
    clq_id = new_id("clq")
    conn.execute(
        """INSERT INTO clarification_questions (id, contract_version_id, kind, field_name, question, status, created_at)
           VALUES (?, ?, ?, ?, ?, 'open', ?)""",
        (clq_id, version_id, kind, field_name, question, now),
    )
    for entity_id in option_ids:
        conn.execute(
            "INSERT OR IGNORE INTO clarification_options (clarification_id, entity_type, entity_id)"
            " VALUES (?, 'extracted_item', ?)",
            (clq_id, entity_id),
        )
    _insert_citations(conn, version_id, "clarification_question", clq_id, citations, seg_ids, segs)


def _persist(
    conn: sqlite3.Connection,
    version: sqlite3.Row,
    segments: list[Segment],
    page_count: int | None,
    result: AnalysisResult,
) -> None:
    version_id = version["id"]
    now = utc_now()
    conn.execute("BEGIN")
    _clear_previous_output(conn, version_id)

    seg_ids: dict[int, str] = {}
    segs = {s.seq: s for s in segments}
    for s in segments:
        seg_ids[s.seq] = new_id("seg")
        conn.execute(
            "INSERT INTO document_segments (id, contract_version_id, seq, page, section, text)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (seg_ids[s.seq], version_id, s.seq, s.page, s.section, s.text),
        )

    item_ids: list[str] = []
    for item in result.items:
        item_id = new_id("itm")
        item_ids.append(item_id)
        value = dumps(item.value)
        conn.execute(
            """INSERT INTO extracted_items (id, contract_version_id, field_name, value_json, original_value_json,
                   display_value, confidence, review_status, ambiguity_note, origin, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, 'ai', ?, ?)""",
            (
                item_id,
                version_id,
                item.field_name,
                value,
                value,
                templates.display_value(item.field_name, item.value),
                item.confidence,
                item.ambiguity_note,
                now,
                now,
            ),
        )
        _insert_citations(conn, version_id, "extracted_item", item_id, item.citations, seg_ids, segs)

    for ob in result.obligations:
        ob_id = new_id("obl")
        rule = dict(ob.due_rule or {"basis": "unspecified", "offset_days": 0})
        if ob.due_date_text:
            rule["due_date_text"] = ob.due_date_text
        conn.execute(
            """INSERT INTO obligations (id, contract_version_id, description, responsible_party, frequency,
                   frequency_text, due_rule_json, confidence, review_status, original_value_json, ambiguity_note,
                   created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
            (
                ob_id,
                version_id,
                ob.description,
                ob.responsible_party,
                ob.frequency,
                ob.frequency_text,
                dumps(rule),
                ob.confidence,
                dumps(ob.original_value),
                ob.ambiguity_note,
                now,
                now,
            ),
        )
        _insert_citations(conn, version_id, "obligation", ob_id, ob.citations, seg_ids, segs)

    for draft in result.clarifications:
        options = [item_ids[i] for i in draft.option_indexes if 0 <= i < len(item_ids)]
        _insert_clarification(
            conn, version_id, draft.kind, draft.field_name, draft.question, options, draft.citations, seg_ids, segs, now
        )

    renewal = calculation_service.recalculate(conn, version_id)
    _add_backend_clarifications(conn, version_id, result, item_ids, renewal, seg_ids, segs, now)

    version_service.compare_with_previous(conn, version_id)
    conn.execute(
        """UPDATE contract_versions SET analysis_status = 'completed', analysis_stage = 'complete',
               analysis_completed_at = ?, page_count = ?, model_name = ?, prompt_version = ? WHERE id = ?""",
        (utc_now(), page_count, result.model_name, result.prompt_version, version_id),
    )
    conn.execute("UPDATE contracts SET updated_at = ? WHERE id = ?", (utc_now(), version["contract_id"]))
    conn.commit()


def _add_backend_clarifications(conn, version_id, result, item_ids, renewal, seg_ids, segs, now) -> None:
    """Clarifications that need date logic: expiration vs effective+term mismatch, and missing term."""
    if renewal.expiration_conflict:
        idx = [
            i
            for i, it in enumerate(result.items)
            if it.field_name in ("expiration_date", "initial_term", "effective_date")
        ]
        options = [
            (
                templates.display_value(result.items[i].field_name, result.items[i].value),
                _first_section(result.items[i].citations, segs),
            )
            for i in idx
        ]
        question = templates.conflict_question("expiration_date", options)
        citations = [c for i in idx for c in result.items[i].citations]
        _insert_clarification(
            conn,
            version_id,
            "conflict",
            "expiration_date",
            question,
            [item_ids[i] for i in idx],
            citations,
            seg_ids,
            segs,
            now,
        )
    has_term = any(it.field_name in ("expiration_date", "initial_term") for it in result.items)
    if not has_term:
        _insert_clarification(
            conn,
            version_id,
            "missing",
            "expiration_date",
            templates.missing_term_question(),
            [],
            [],
            seg_ids,
            segs,
            now,
        )


def _first_section(citations: list[Citation], segs: dict[int, Segment]) -> str | None:
    for c in citations:
        if c.segment_seq in segs and segs[c.segment_seq].section:
            return segs[c.segment_seq].section
    return None


def status(conn: sqlite3.Connection, contract_id: str, version_id: str | None) -> dict:
    version = get_version(conn, contract_id, version_id)
    vid = version["id"]
    out = {
        "contract_id": contract_id,
        "version_id": vid,
        "analysis_status": version["analysis_status"],
        "analysis_stage": version["analysis_stage"],
        "progress": None,
        "error": None,
        "started_at": version["analysis_started_at"],
        "completed_at": version["analysis_completed_at"],
        "summary": None,
    }
    if version["analysis_status"] == "processing" and version["analysis_stage"] == "extracting":
        p = progress_for(vid)
        if p:
            out["progress"] = {"current": p[0], "total": p[1]}
    if version["analysis_status"] == "failed":
        out["error"] = {"code": version["analysis_error_code"], "message": version["analysis_error_message"]}
    if version["analysis_status"] == "completed":
        renewal = conn.execute(
            "SELECT calculation_status FROM renewals WHERE contract_version_id = ?", (vid,)
        ).fetchone()
        out["summary"] = {
            **version_counts(conn, vid),
            "citations_not_found": conn.execute(
                "SELECT COUNT(*) FROM citations WHERE contract_version_id = ? AND validation_status = 'not_found'",
                (vid,),
            ).fetchone()[0],
            "renewal_calculation_status": renewal["calculation_status"] if renewal else None,
        }
    return out
