from pathlib import Path

from ai.types import AnalysisResult, Citation, ExtractedCandidate, ObligationCandidate
from backend.core.config import settings
from backend.services import analysis_service
from db.database import connect

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "contracts/samples/simple/acme-services-agreement.pdf"
DOCX = ROOT / "contracts/samples/simple/acme-services-agreement.docx"


def fake_result(segments, notice_days=90):
    def cite(section, quote):
        seg = next(s for s in segments if s.section == section)
        start = seg.text.find(quote)
        return [Citation(seg.seq, quote, start, start + len(quote), "verified")]

    items = [
        ExtractedCandidate(
            "party",
            {"name": "Acme Corporation", "role": "customer"},
            "high",
            None,
            cite("SERVICES AGREEMENT", "Acme Corporation"),
        ),
        ExtractedCandidate(
            "expiration_date",
            {"date": "2027-01-31", "date_text": "January 31, 2027"},
            "high",
            None,
            cite("2.1 Term", "January 31, 2027"),
        ),
        ExtractedCandidate(
            "renewal_terms",
            {"type": "automatic", "period_value": 12, "period_unit": "months"},
            "high",
            None,
            cite("2.2 Renewal", "automatically renew"),
        ),
        ExtractedCandidate(
            "notice_period",
            {"value": notice_days, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal"},
            "high",
            None,
            cite("2.2 Renewal", "ninety (90) days"),
        ),
    ]
    obligations = [
        ObligationCandidate(
            "Submit quarterly compliance report",
            "Example Services Ltd.",
            "quarterly",
            "within thirty (30) days after the end of each calendar quarter",
            {"basis": "calendar_period_end", "offset_days": 30},
            None,
            "high",
            None,
            {"description": "Submit quarterly compliance report"},
            cite("4.2 Reporting Obligations", "compliance report"),
        )
    ]
    return AnalysisResult(items, obligations, [], "fake", "terms-v1+obligations-v1", {})


def upload(client, path, name):
    with path.open("rb") as f:
        return client.post("/api/contracts", files={"file": (name, f)})


def test_review_all_acme_pending_inputs_and_obligations(client):
    before = client.get("/api/dashboard").json()["counts"]["contracts_needing_review"]
    queue = client.get("/api/reviews/queue?contract_id=ctr_acme").json()["items"]
    assert len(queue) == 8
    for item in queue:
        response = client.post(
            "/api/reviews",
            json={"entity_type": item["entity_type"], "entity_id": item["entity_id"], "action": "approve"},
        )
        assert response.status_code == 200, response.text
    assert client.get("/api/reviews/queue?contract_id=ctr_acme").json()["items"] == []
    detail = client.get("/api/contracts/ctr_acme").json()
    assert detail["renewal"]["inputs_reviewed"] is True
    assert client.get("/api/dashboard").json()["counts"]["contracts_needing_review"] == before - 1


def test_reject_and_reapprove_notice_recalculates_obligation(client):
    body = {"entity_type": "extracted_item", "entity_id": "itm_acme_notice", "action": "reject"}
    assert client.post("/api/reviews", json=body).status_code == 200
    assert client.get("/api/contracts/ctr_acme").json()["renewal"]["notice_deadline"] is None
    obligation = client.get("/api/obligations/obl_acme_nonrenewal").json()
    assert obligation["due_date"] is None
    body["action"] = "approve"
    assert client.post("/api/reviews", json=body).status_code == 200
    assert client.get("/api/contracts/ctr_acme").json()["renewal"]["notice_deadline"] == "2026-11-02"


def test_edit_obligation_preserves_original_and_records_value_history(client):
    original = client.get("/api/obligations/obl_acme_report").json()["original_value"]
    changed_date = client.post(
        "/api/reviews",
        json={
            "entity_type": "obligation",
            "entity_id": "obl_acme_report",
            "action": "edit",
            "value": {"due_date": "2026-12-15"},
        },
    )
    assert changed_date.status_code == 200, changed_date.text
    assert changed_date.json()["item"]["due_date"] == "2026-12-15"
    assert changed_date.json()["item"]["due_date_source"] == "explicit"
    assert changed_date.json()["item"]["original_value"] == original
    changed_desc = client.post(
        "/api/reviews",
        json={
            "entity_type": "obligation",
            "entity_id": "obl_acme_report",
            "action": "edit",
            "value": {"description": "Submit revised quarterly report"},
        },
    )
    assert changed_desc.status_code == 200, changed_desc.text
    history = client.get("/api/reviews?entity_type=obligation&entity_id=obl_acme_report").json()["items"]
    edit = next(x for x in history if x["action"] == "edit")
    assert edit["previous_value"]["description"] == original["description"]
    assert edit["new_value"]["description"] == "Submit revised quarterly report"


def test_custom_globex_clarification(client):
    response = client.post(
        "/api/clarifications/clq_globex_notice/resolve",
        json={
            "action": "custom",
            "value": {"value": 45, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal"},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["renewal"]["notice_deadline"] == "2026-11-16"
    items = client.get("/api/contracts/ctr_globex/extracted-items?field_name=notice_period").json()["items"]
    options = {x["id"]: x for x in items}
    assert options["itm_globex_notice_90"]["review_status"] == "rejected"
    assert options["itm_globex_notice_60"]["review_status"] == "rejected"
    human = next(x for x in items if x["origin"] == "human")
    assert human["review_status"] == "edited"


def test_dismiss_globex_clarification_keeps_conflict_blocked(client):
    response = client.post("/api/clarifications/clq_globex_notice/resolve", json={"action": "dismiss"})
    assert response.status_code == 200, response.text
    assert response.json()["clarification"]["status"] == "dismissed"
    assert client.get("/api/contracts/ctr_globex").json()["renewal"]["calculation_status"] == "blocked_by_conflict"


def test_reanalysis_replaces_output_and_retains_review_rows(client, monkeypatch):
    monkeypatch.setattr(analysis_service, "analyze", lambda segs, on_progress=None: fake_result(segs))
    cid = upload(client, PDF, "reviewed.pdf").json()["contract"]["id"]
    assert client.post(f"/api/contracts/{cid}/analyze").status_code == 202
    item = client.get(f"/api/contracts/{cid}/extracted-items").json()["items"][0]
    assert (
        client.post(
            "/api/reviews", json={"entity_type": "extracted_item", "entity_id": item["id"], "action": "approve"}
        ).status_code
        == 200
    )
    old_ids = {x["id"] for x in client.get(f"/api/contracts/{cid}/extracted-items").json()["items"]}
    conn = connect(settings.database_path)
    try:
        reviews_before = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    finally:
        conn.close()
    assert client.post(f"/api/contracts/{cid}/analyze").status_code == 202
    new_ids = {x["id"] for x in client.get(f"/api/contracts/{cid}/extracted-items").json()["items"]}
    conn = connect(settings.database_path)
    try:
        reviews_after = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    finally:
        conn.close()
    assert old_ids.isdisjoint(new_ids)
    assert reviews_after == reviews_before


def test_version_changes_stale_review_and_version_specific_details(client, monkeypatch):
    monkeypatch.setattr(analysis_service, "analyze", lambda segs, on_progress=None: fake_result(segs, 90))
    cid = upload(client, PDF, "v1.pdf").json()["contract"]["id"]
    client.post(f"/api/contracts/{cid}/analyze")
    notice = next(
        x
        for x in client.get(f"/api/contracts/{cid}/extracted-items").json()["items"]
        if x["field_name"] == "notice_period"
    )
    client.post("/api/reviews", json={"entity_type": "extracted_item", "entity_id": notice["id"], "action": "approve"})
    v1 = client.get(f"/api/contracts/{cid}").json()["version"]["id"]
    with DOCX.open("rb") as f:
        v2 = client.post(f"/api/contracts/{cid}/versions", files={"file": ("v2.docx", f)})
    assert v2.status_code == 201, v2.text
    monkeypatch.setattr(analysis_service, "analyze", lambda segs, on_progress=None: fake_result(segs, 60))
    client.post(f"/api/contracts/{cid}/analyze")
    changes = client.get(f"/api/contracts/{cid}/versions/{v2.json()['id']}/changes").json()["items"]
    notice_change = next(x for x in changes if x["field_name"] == "notice_period")
    assert notice_change["change_type"] == "modified"
    assert notice_change["previous_review_status"] == "approved"
    latest = client.get(f"/api/contracts/{cid}").json()
    old = client.get(f"/api/contracts/{cid}?version_id={v1}").json()
    assert latest["version"]["id"] == v2.json()["id"]
    assert latest["renewal"]["notice_period"]["value"] == 60
    assert old["version"]["id"] == v1
    assert old["renewal"]["notice_period"]["value"] == 90
