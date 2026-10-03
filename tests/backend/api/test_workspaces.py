"""Workspace isolation on the public deployment: two browsers never see or change each other's data."""

import dataclasses
import uuid

import pytest

from backend.core import limits, workspace
from backend.core.limits import RateLimiter
from backend.services import analysis_service
from tests.backend.api.test_api import ACME_PDF, _fake_result, err


def ws() -> str:
    return f"ws_{uuid.uuid4().hex}"


@pytest.fixture
def public(client, monkeypatch, tmp_path):
    """The same app, configured as the public deployment (WORKSPACES=true)."""
    settings = dataclasses.replace(workspace.settings, workspaces=True, workspace_dir=str(tmp_path / "ws"))
    monkeypatch.setattr(workspace, "settings", settings)
    monkeypatch.setattr(workspace, "workspace_limiter", RateLimiter(1000, 3600))
    monkeypatch.setattr(workspace, "analysis_limiter", RateLimiter(1000, 3600))
    monkeypatch.setattr(analysis_service, "analyze", lambda segs, on_progress=None: _fake_result(segs))
    return client


def h(workspace_id):
    return {"X-Workspace-ID": workspace_id}


def upload_and_analyze(client, headers):
    with ACME_PDF.open("rb") as f:
        cid = client.post("/api/contracts", files={"file": ("acme.pdf", f)}, headers=headers).json()["contract"]["id"]
    assert client.post(f"/api/contracts/{cid}/analyze", headers=headers).status_code == 202
    return cid


def test_each_workspace_starts_with_its_own_demo_copy(public):
    a, b = ws(), ws()
    for w in (a, b):
        names = [c["name"] for c in public.get("/api/contracts", headers=h(w)).json()["items"]]
        assert sorted(names) == ["Acme Services Agreement", "Globex Hosting Agreement"]


def test_uploads_are_invisible_to_other_workspaces(public):
    a, b = ws(), ws()
    cid = upload_and_analyze(public, h(a))
    assert public.get(f"/api/contracts/{cid}/analysis", headers=h(a)).json()["analysis_status"] == "completed"

    listed_b = [c["id"] for c in public.get("/api/contracts", headers=h(b)).json()["items"]]
    assert cid not in listed_b
    for path in (
        f"/api/contracts/{cid}",
        f"/api/contracts/{cid}/extracted-items",
        f"/api/contracts/{cid}/versions",
        f"/api/contracts/{cid}/analysis",
    ):
        assert public.get(path, headers=h(b)).status_code == 404, path
    assert err(public.post(f"/api/contracts/{cid}/analyze", headers=h(b))) == "CONTRACT_NOT_FOUND"


def test_ids_from_another_workspace_resolve_to_not_found(public):
    a, b = ws(), ws()
    cid = upload_and_analyze(public, h(a))
    item = public.get(f"/api/contracts/{cid}/extracted-items", headers=h(a)).json()["items"][0]
    obligation = public.get(f"/api/obligations?contract_id={cid}", headers=h(a)).json()["items"][0]
    citation_id = item["citations"][0]["id"]

    assert public.get(f"/api/citations/{citation_id}", headers=h(a)).status_code == 200
    assert err(public.get(f"/api/citations/{citation_id}", headers=h(b))) == "CITATION_NOT_FOUND"
    assert err(public.get(f"/api/obligations/{obligation['id']}", headers=h(b))) == "OBLIGATION_NOT_FOUND"
    assert err(public.get(f"/api/items/extracted_item/{item['id']}", headers=h(b))) == "ITEM_NOT_FOUND"
    review = {"entity_type": "extracted_item", "entity_id": item["id"], "action": "approve"}
    assert err(public.post("/api/reviews", json=review, headers=h(b))) == "ITEM_NOT_FOUND"
    assert all(o["contract_id"] != cid for o in public.get("/api/obligations", headers=h(b)).json()["items"])
    assert all(q["contract_id"] != cid for q in public.get("/api/reviews/queue", headers=h(b)).json()["items"])


def test_review_decisions_stay_in_their_workspace(public):
    a, b = ws(), ws()
    clr = public.get("/api/clarifications?status=open", headers=h(a)).json()["items"][0]
    option = clr["options"][0]["entity_id"]
    body = {"action": "select", "entity_id": option}
    assert public.post(f"/api/clarifications/{clr['id']}/resolve", json=body, headers=h(a)).status_code == 200

    assert public.get("/api/clarifications?status=open", headers=h(a)).json()["items"] == []
    still_open = public.get("/api/clarifications?status=open", headers=h(b)).json()["items"]
    assert [q["id"] for q in still_open] == [clr["id"]]
    acme_b = public.get("/api/contracts/ctr_globex", headers=h(b)).json()
    assert acme_b["renewal"]["calculation_status"] == "blocked_by_conflict"


def test_invalid_workspace_ids_are_rejected(public):
    for bad in ("../../etc/passwd", "ws_short", "ws_" + "x" * 80, "nope"):
        assert err(public.get("/api/contracts", headers=h(bad))) == "INVALID_WORKSPACE", bad


def test_requests_without_a_workspace_use_the_default_database(public):
    cid = upload_and_analyze(public, {})
    assert public.get(f"/api/contracts/{cid}").status_code == 200
    assert public.get(f"/api/contracts/{cid}", headers=h(ws())).status_code == 404


def test_header_is_ignored_when_workspaces_are_off(client):
    cid = upload_and_analyze(client, h(ws()))
    assert client.get(f"/api/contracts/{cid}", headers=h(ws())).status_code == 200


def test_analysis_rate_limit(public, monkeypatch):
    monkeypatch.setattr(workspace, "analysis_limiter", RateLimiter(1, 3600))
    a = ws()
    cid = upload_and_analyze(public, h(a))
    assert err(public.post(f"/api/contracts/{cid}/analyze", headers=h(a))) == "RATE_LIMITED"


def test_new_workspace_rate_limit_per_address(public, monkeypatch):
    monkeypatch.setattr(workspace, "workspace_limiter", RateLimiter(1, 3600))
    assert public.get("/api/contracts", headers=h(ws())).status_code == 200
    assert err(public.get("/api/contracts", headers=h(ws()))) == "RATE_LIMITED"


def test_oversized_upload_rejected_before_reading_the_body(client):
    too_big = str(limits.settings.max_upload_mb * 1024 * 1024 + 2 * 1024 * 1024)
    resp = client.post("/api/contracts", content=b"x", headers={"Content-Length": too_big})
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert resp.headers["X-Request-ID"] == resp.json()["error"]["request_id"]
