"""API tests over the demo seed (Acme clean, Globex conflict). Reference today: 2026-10-03."""

from pathlib import Path

from ai.types import AnalysisResult, Citation, ExtractedCandidate, ObligationCandidate
from backend.services import analysis_service

ROOT = Path(__file__).resolve().parents[3]
ACME_PDF = ROOT / "contracts/samples/simple/acme-services-agreement.pdf"


def err(resp):
    return resp.json()["error"]["code"]


# ---------------------------------------------------------------- reads over seed


def test_health_and_list(client):
    assert client.get("/api/health").json()["database"] == "ok"
    items = client.get("/api/contracts").json()["items"]
    acme = next(c for c in items if c["id"] == "ctr_acme")
    assert acme["notice_deadline"] == "2026-11-02"
    assert acme["days_until_notice_deadline"] == 30
    assert acme["lifecycle_status"] == "expiring_soon"
    assert acme["parties"] == ["Acme Corporation", "Example Services Ltd."]
    assert acme["pending_review_count"] == 8
    assert [c["id"] for c in client.get("/api/contracts?search=initech").json()["items"]] == ["ctr_globex"]


def test_contract_detail_and_items(client):
    d = client.get("/api/contracts/ctr_acme").json()
    assert d["renewal"]["calculation_status"] == "calculated"
    assert d["renewal"]["inputs_reviewed"] is False
    assert d["counts"]["pending_reviews"] == 8
    items = client.get("/api/contracts/ctr_acme/extracted-items").json()["items"]
    assert items[0]["field_name"] == "party"
    notice = next(i for i in items if i["field_name"] == "notice_period")
    assert notice["citations"][0]["section"] == "2.2 Renewal"
    assert err(client.get("/api/contracts/nope")) == "CONTRACT_NOT_FOUND"


def test_globex_blocked_and_clarification(client):
    renewals = {r["contract_id"]: r for r in client.get("/api/renewals").json()["items"]}
    assert renewals["ctr_globex"]["calculation_status"] == "blocked_by_conflict"
    assert renewals["ctr_globex"]["notice_deadline"] is None
    clq = client.get("/api/clarifications?status=open").json()["items"]
    assert len(clq) == 1 and len(clq[0]["options"]) == 2


def test_dashboard(client):
    d = client.get("/api/dashboard").json()
    assert d["counts"] == {
        "contracts": 2,
        "contracts_needing_review": 2,
        "upcoming_notice_deadlines": 1,
        "open_obligations": 3,
        "open_clarifications": 1,
    }
    assert [x["date"] for x in d["upcoming_deadlines"]] == sorted(x["date"] for x in d["upcoming_deadlines"])
    assert d["recent_activity"][0]["type"] in ("upload", "analysis", "review", "clarification")


def test_obligations_and_citation(client):
    obls = client.get("/api/obligations?contract_id=ctr_acme").json()["items"]
    assert obls[0]["due_date"] == "2026-10-30" and obls[0]["days_until_due"] == 27
    c = client.get("/api/citations/cit_acme_notice").json()
    seg = c["segment"]
    assert seg["text"][seg["highlight"]["start"] : seg["highlight"]["end"]] == c["source_text"]
    assert err(client.get("/api/citations/x")) == "CITATION_NOT_FOUND"


# ---------------------------------------------------------------- review & clarification


def test_review_actions(client):
    r = client.post(
        "/api/reviews",
        json={
            "entity_type": "extracted_item",
            "entity_id": "itm_acme_notice",
            "action": "edit",
            "value": {"value": 60, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal"},
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["item"]["review_status"] == "edited"
    assert body["item"]["original_value"]["value"] == 90
    assert body["renewal"]["notice_deadline"] == "2026-12-02"
    hist = client.get("/api/reviews?entity_type=extracted_item&entity_id=itm_acme_notice").json()["items"]
    assert hist[0]["previous_value"]["value"] == 90

    r = client.post(
        "/api/reviews",
        json={"entity_type": "extracted_item", "entity_id": "itm_acme_notice", "action": "approve", "value": {"x": 1}},
    )
    assert err(r) == "INVALID_REVIEW_ACTION"
    r = client.post(
        "/api/reviews",
        json={
            "entity_type": "extracted_item",
            "entity_id": "itm_acme_exp",
            "action": "edit",
            "value": {"date": "2027-02-30"},
        },
    )
    assert err(r) == "VALIDATION_ERROR"
    r = client.patch("/api/obligations/obl_acme_report", json={"description": "x"})
    assert err(r) == "VALIDATION_ERROR"
    r = client.patch("/api/obligations/obl_acme_report", json={"status": "completed"})
    assert r.json()["status"] == "completed"


def test_resolve_conflict(client):
    r = client.post(
        "/api/clarifications/clq_globex_notice/resolve", json={"action": "select", "entity_id": "itm_globex_notice_60"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["renewal"]["notice_deadline"] == "2026-11-01"
    assert r.json()["clarification"]["status"] == "resolved"
    r = client.post("/api/clarifications/clq_globex_notice/resolve", json={"action": "dismiss"})
    assert err(r) == "CLARIFICATION_ALREADY_CLOSED"


# ---------------------------------------------------------------- upload + analysis (fake model)


def _fake_result(segments):
    seq = {s.section: s.seq for s in segments}

    def cite(section, quote):
        s = next(x for x in segments if x.seq == seq[section])
        i = s.text.find(quote)
        return [Citation(s.seq, quote, i, i + len(quote), "verified")]

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
            {"value": 90, "unit": "days", "anchor": "expiration_date", "purpose": "non_renewal"},
            "high",
            None,
            cite("2.2 Renewal", "ninety (90) days"),
        ),
    ]
    obls = [
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
    return AnalysisResult(items, obls, [], "fake", "terms-v1+obligations-v1", {})


def test_upload_analyze_and_new_version(client, monkeypatch):
    monkeypatch.setattr(analysis_service, "analyze", lambda segs, on_progress=None: _fake_result(segs))
    with ACME_PDF.open("rb") as f:
        r = client.post("/api/contracts", files={"file": ("acme.pdf", f, "application/pdf")})
    assert r.status_code == 201, r.text
    cid = r.json()["contract"]["id"]
    assert r.json()["version"]["analysis_status"] == "not_started"

    r = client.post(f"/api/contracts/{cid}/analyze")
    assert r.status_code == 202, r.text
    a = client.get(f"/api/contracts/{cid}/analysis").json()
    assert a["analysis_status"] == "completed", a
    assert a["summary"]["obligations"] == 1
    d = client.get(f"/api/contracts/{cid}").json()
    assert d["renewal"]["notice_deadline"] == "2026-11-02"
    assert d["version"]["file_name"] == "acme.pdf"
    clq = client.get(f"/api/clarifications?contract_id={cid}").json()["items"]
    assert clq == []

    # Duplicate version rejected; a changed version produces a diff.
    with ACME_PDF.open("rb") as f:
        assert err(client.post(f"/api/contracts/{cid}/versions", files={"file": ("a.pdf", f)})) == "DUPLICATE_VERSION"
    docx = ROOT / "contracts/samples/simple/acme-services-agreement.docx"
    with docx.open("rb") as f:
        v2 = client.post(f"/api/contracts/{cid}/versions", files={"file": ("acme-v2.docx", f)}).json()
    assert v2["version_number"] == 2

    def changed(segs):
        res = _fake_result(segs)
        res.items[3].value = {**res.items[3].value, "value": 60}
        return res

    monkeypatch.setattr(analysis_service, "analyze", lambda segs, on_progress=None: changed(segs))
    client.post(f"/api/contracts/{cid}/analyze")
    ch = client.get(f"/api/contracts/{cid}/versions/{v2['id']}/changes").json()
    assert [(c["field_name"], c["change_type"]) for c in ch["items"]] == [("notice_period", "modified")]
    assert len(client.get(f"/api/contracts/{cid}/versions").json()["items"]) == 2


def test_upload_errors(client):
    assert err(client.post("/api/contracts", files={"file": ("x.pdf", b"MZ not a pdf")})) == "INVALID_DOCUMENT"
    assert err(client.post("/api/contracts", files={"file": ("x.pdf", b"")})) == "EMPTY_UPLOAD"
    assert err(client.post("/api/contracts")) == "EMPTY_UPLOAD"


def test_analysis_failure_persists_nothing(client, monkeypatch):
    from ai.errors import InvalidAIOutput

    def boom(segs, on_progress=None):
        raise InvalidAIOutput("bad output")

    monkeypatch.setattr(analysis_service, "analyze", boom)
    with ACME_PDF.open("rb") as f:
        cid = client.post("/api/contracts", files={"file": ("acme.pdf", f)}).json()["contract"]["id"]
    client.post(f"/api/contracts/{cid}/analyze")
    a = client.get(f"/api/contracts/{cid}/analysis").json()
    assert a["analysis_status"] == "failed" and a["error"]["code"] == "INVALID_AI_OUTPUT"
    assert client.get(f"/api/contracts/{cid}/extracted-items").json()["items"] == []


def test_recent_reviews(client):
    items = client.get("/api/reviews/recent").json()["items"]
    assert items[0]["entity_id"] == "itm_acme_eff" and items[0]["label"] == "Effective date"
    assert items[0]["contract_name"] == "Acme Services Agreement"


def test_item_detail(client):
    r = client.get("/api/items/extracted_item/itm_acme_notice").json()
    assert r["contract_name"] == "Acme Services Agreement" and r["version_number"] == 1
    assert r["item"]["original_display_value"] == "90 days before expiration (non-renewal)"
    assert client.get("/api/items/obligation/obl_acme_report").json()["item"]["description"]
    assert err(client.get("/api/items/obligation/nope")) == "ITEM_NOT_FOUND"
