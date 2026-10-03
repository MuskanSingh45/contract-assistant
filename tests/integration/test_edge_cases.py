from pathlib import Path

import pymupdf

from backend.core.config import settings
from backend.services import analysis_service
from db.database import connect

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "contracts/samples/simple/acme-services-agreement.pdf"


def err(response):
    return response.json()["error"]["code"]


def upload(client, data, filename, content_type="application/pdf"):
    return client.post("/api/contracts", files={"file": (filename, data, content_type)})


def test_analysis_in_progress_conflict(client):
    cid = "ctr_acme"
    conn = connect(settings.database_path)
    try:
        conn.execute("UPDATE contract_versions SET analysis_status='processing' WHERE id='ver_acme_1'")
        conn.commit()
    finally:
        conn.close()
    response = client.post(f"/api/contracts/{cid}/analyze")
    assert response.status_code == 409
    assert err(response) == "ANALYSIS_IN_PROGRESS"


def test_ai_unavailable(client, monkeypatch):
    monkeypatch.setattr(analysis_service, "check_available", lambda: (False, False))
    response = client.post("/api/contracts/ctr_acme/analyze")
    assert response.status_code == 503
    assert err(response) == "AI_UNAVAILABLE"


def test_changes_require_completed_analysis(client):
    result = upload(client, PDF.read_bytes(), "pending.pdf")
    cid = result.json()["contract"]["id"]
    version_id = result.json()["version"]["id"]
    response = client.get(f"/api/contracts/{cid}/versions/{version_id}/changes")
    assert response.status_code == 409
    assert err(response) == "ANALYSIS_NOT_COMPLETE"


def test_empty_text_pdf_fails_analysis_without_persisting(client, monkeypatch):
    doc = pymupdf.open()
    doc.new_page()
    pdf_bytes = doc.tobytes()
    doc.close()
    cid = upload(client, pdf_bytes, "blank.pdf").json()["contract"]["id"]
    response = client.post(f"/api/contracts/{cid}/analyze")
    assert response.status_code == 202
    result = client.get(f"/api/contracts/{cid}/analysis").json()
    assert result["analysis_status"] == "failed"
    assert result["error"]["code"] == "NO_EXTRACTABLE_TEXT"
    assert client.get(f"/api/contracts/{cid}/extracted-items").json()["items"] == []
    assert client.get(f"/api/obligations?contract_id={cid}").json()["items"] == []


def test_file_too_large_uses_configured_limit(client, monkeypatch):
    original = settings.max_upload_mb
    object.__setattr__(settings, "max_upload_mb", 1)
    try:
        response = upload(client, b"%PDF-" + b"0" * (1024 * 1024 + 1), "large.pdf")
        assert response.status_code == 413
        assert err(response) == "FILE_TOO_LARGE"
    finally:
        object.__setattr__(settings, "max_upload_mb", original)


def test_obligation_operational_status_cycle(client):
    for status in ("completed", "not_applicable", "open"):
        response = client.patch("/api/obligations/obl_acme_report", json={"status": status})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status


def test_obligations_due_before_filters_inclusive(client):
    items = client.get("/api/obligations?due_before=2026-10-31").json()["items"]
    assert items
    assert all(x["due_date"] is not None and x["due_date"] <= "2026-10-31" for x in items)
    assert any(x["id"] == "obl_acme_report" for x in items)


def test_renewals_within_days_includes_acme_excludes_globex(client):
    items = client.get("/api/renewals?within_days=40").json()["items"]
    contract_ids = {x["contract_id"] for x in items}
    assert "ctr_acme" in contract_ids
    assert "ctr_globex" not in contract_ids


def test_review_history_newest_first(client):
    for action in ("approve", "reject"):
        response = client.post(
            "/api/reviews", json={"entity_type": "extracted_item", "entity_id": "itm_acme_exp", "action": action}
        )
        assert response.status_code == 200, response.text
    history = client.get("/api/reviews?entity_type=extracted_item&entity_id=itm_acme_exp").json()["items"]
    assert [x["action"] for x in history[:2]] == ["reject", "approve"]


def test_malformed_review_returns_documented_validation_error(client):
    response = client.post("/api/reviews", json={"entity_type": "made_up", "entity_id": 3, "action": "approve"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "message" in body["error"]
