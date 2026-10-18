from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.main import create_app
from commerce_data.ingestion.engine import IngestionEngine
from commerce_data.storage.models import Record, Run, Source, SyncState


def workspace(db, settings):
    client = TestClient(create_app(settings, db))
    response = client.get("/api/v1/session")
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf"]
    return client


def test_shared_workspace_no_login_and_csrf(db, settings):
    client = TestClient(create_app(settings, db))
    home = client.get("/")
    assert home.status_code == 200
    assert "login-form" not in home.text and "Dùng chung nội bộ" in home.text
    assert "frame-ancestors 'none'" in home.headers["content-security-policy"]
    assert client.get("/assets/app.js").status_code == 200
    session = client.get("/api/v1/session")
    assert session.json()["role"] == "workspace"
    assert "HttpOnly" in session.headers["set-cookie"]
    assert "SameSite=strict" in session.headers["set-cookie"]
    assert "test-admin" not in session.text
    assert client.get("/api/v1/overview").status_code == 200
    body = b"id,name\n1,Demo\n"
    assert client.post("/api/v1/imports/csv/preview", content=body).status_code == 403
    assert (
        client.post(
            "/api/v1/imports/csv/preview",
            content=body,
            headers={"X-CSRF-Token": session.json()["csrf"]},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/session").json()["csrf"] == session.json()["csrf"]
    assert (
        client.get("/api/v1/session", headers={"Origin": "https://outside.test"}).status_code == 403
    )
    assert (
        client.get("/api/v1/session", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    )
    assert client.post("/api/v1/session", json={"access_code": "anything"}).status_code == 405


def test_csv_preview_import_and_worker_dedup(db, settings):
    client = workspace(db, settings)
    body = "\ufeffid;name\n1;Nguyễn An\n2;<script>alert(1)</script>\n".encode()
    preview = client.post("/api/v1/imports/csv/preview", content=body)
    assert preview.status_code == 200, preview.text
    assert preview.json()["delimiter"] == ";"
    assert preview.json()["row_count"] == 2
    assert preview.json()["sample"][0][1] == "Nguyễn An"
    imported = client.post(
        "/api/v1/imports/csv", params={"name": "Đội nội bộ", "key_field": "id"}, content=body
    )
    assert imported.status_code == 201, imported.text
    data = imported.json()
    saved = list((settings.csv_root / "uploads").glob("*.csv"))
    assert len(saved) == 1 and saved[0].read_bytes() == body
    ingestion = IngestionEngine(db, settings)
    ingestion.run(data["job_id"])
    run = client.get("/api/v1/pipelines/runs/" + data["job_id"]).json()
    assert run["status"] == "succeeded", run
    assert run["rows_inserted"] == 2
    again = client.post("/api/v1/sources/" + data["source_id"] + "/sync")
    ingestion.run(again.json()["job_id"])
    assert (
        client.get("/api/v1/pipelines/runs/" + again.json()["job_id"]).json()["rows_inserted"] == 0
    )
    duplicate = client.post(
        "/api/v1/imports/csv", params={"name": "Đội nội bộ", "key_field": "id"}, content=body
    )
    assert duplicate.status_code == 409
    assert len(list((settings.csv_root / "uploads").glob("*.csv"))) == 1
    overview = client.get("/api/v1/overview").json()
    assert overview["raw_versions"] == 2 and overview["updated_sources"] == 1
    assert overview["day_timezone"] == "Asia/Ho_Chi_Minh"
    filtered = client.get("/api/v1/sources", params={"q": "nội bộ", "kind": "csv"}).json()
    assert filtered["total"] == 1
    assert filtered["states"][data["source_id"]]["latest_run"]["status"] == "succeeded"
    assert client.get("/api/v1/sources?q=unmatched").json()["total"] == 0
    assert client.get("/api/v1/pipelines/runs?status=failed").json()["total"] == 0
    with Session(db) as session:
        assert session.scalar(select(func.count()).select_from(Record)) == 2


@pytest.mark.parametrize(
    ("body", "code"),
    [
        (b"id,id\n1,2\n", "csv_duplicate_headers"),
        (b"id,name\n", "csv_empty"),
        (b"id,name\n1,x,y\n", "csv_width"),
        (b"id,name\n1,\xff\n", "csv_encoding"),
        (b"id,name\n1,x\n1,y\n", "csv_key_duplicate"),
        (b"id,name\n,x\n", "csv_key_empty"),
    ],
)
def test_invalid_csv_leaves_no_source_or_upload(db, settings, body, code):
    client = workspace(db, settings)
    result = client.post(
        "/api/v1/imports/csv", params={"name": "Invalid", "key_field": "id"}, content=body
    )
    assert result.status_code == 422 and result.json()["error"]["message"] == code
    assert not list(settings.csv_root.rglob("*.csv"))
    with Session(db) as session:
        assert not session.scalars(select(Source)).all()


def test_upload_limit(db, settings):
    settings.upload_limit_bytes = 10
    client = workspace(db, settings)
    response = client.post("/api/v1/imports/csv/preview", content=b"id,name\n1,large\n")
    assert response.status_code == 413


def test_overview_latest_failure_paused_and_vietnam_day(db, settings, source, monkeypatch):
    now = datetime(2026, 10, 15, 18, 0, tzinfo=UTC)
    monkeypatch.setattr("apps.api.ui.utcnow", lambda: now)
    with Session(db) as session, session.begin():
        state = session.get(SyncState, source.id)
        state.last_success_at = now - timedelta(hours=1)
        session.add(
            Run(
                source_id=source.id,
                status="succeeded",
                kind="sync",
                created_at=now - timedelta(hours=2),
            )
        )
        session.add(Run(source_id=source.id, status="failed", kind="sync", created_at=now))
    client = workspace(db, settings)
    overview = client.get("/api/v1/overview").json()
    assert overview["runs_today"] == {"failed": 1}
    assert overview["attention_count"] == 1
    assert overview["attention"][0]["reason"] == "failed"
    response = client.patch("/api/v1/sources/" + source.id, json={"enabled": False})
    assert response.status_code == 200
    assert client.get("/api/v1/overview").json()["attention_count"] == 0
    assert client.post("/api/v1/sources/" + source.id + "/sync").status_code == 409


def test_google_setup_exposes_names_only(db, settings, monkeypatch):
    monkeypatch.setenv("CDIP_SECRET_GOOGLE_TEST", "private-value-do-not-display")
    client = workspace(db, settings)
    result = client.get("/api/v1/connections")
    assert "env:CDIP_SECRET_GOOGLE_TEST" in result.json()["google"]
    assert "private-value-do-not-display" not in result.text
