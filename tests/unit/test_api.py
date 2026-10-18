import hashlib
import hmac
import json
import time

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.main import create_app
from commerce_data.ingestion.engine import IngestionEngine
from commerce_data.storage.models import Record, Source, Webhook
from tests.unit.test_connectors import record

ADMIN = {"Authorization": "Bearer test-admin"}
READER = {"Authorization": "Bearer test-reader"}


def test_auth_validation_and_jobs(db, settings):
    client = TestClient(create_app(settings, db))
    body = {"name": "api-test", "config": {"kind": "rest", "base_url": "https://mock.test"}}
    assert client.get("/api/v1/sources").status_code == 401
    assert client.post("/api/v1/sources", json=body, headers=READER).status_code == 403
    created = client.post("/api/v1/sources", json=body, headers=ADMIN)
    assert created.status_code == 201, created.text
    source_id = created.json()["id"]
    assert client.post("/api/v1/sources", json=body, headers=ADMIN).status_code == 409
    job = client.post(f"/api/v1/sources/{source_id}/sync", headers=ADMIN)
    assert job.status_code == 202
    assert (
        client.get(f"/api/v1/pipelines/runs/{job.json()['job_id']}", headers=READER).json()[
            "status"
        ]
        == "queued"
    )
    body["config"]["api_key"] = "DO-NOT-ECHO-ME"
    error = client.post("/api/v1/sources", json=body, headers=ADMIN)
    assert error.status_code == 422 and "DO-NOT-ECHO-ME" not in error.text
    assert client.post("/api/v1/ai/analyze", headers=READER).status_code == 503
    assert client.get("/api/v1/sources?limit=1000", headers=READER).status_code == 422
    assert (
        client.patch(
            f"/api/v1/sources/{source_id}", json={"enabled": False}, headers=ADMIN
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/sources/{source_id}/sync", headers=ADMIN).status_code == 409


def test_webhook_durable_idempotent_and_authenticated(db, source, settings, monkeypatch):
    monkeypatch.setenv("CDIP_SECRET_WEBHOOK", "test-only-secret")
    with Session(db) as session, session.begin():
        obj = session.get(Source, source.id)
        obj.config = {**obj.config, "webhook_secret_ref": "env:CDIP_SECRET_WEBHOOK"}
    client = TestClient(create_app(settings, db))
    body = json.dumps(record(1)).encode()
    sent_at = str(int(time.time()))
    signature = hmac.new(
        b"test-only-secret", sent_at.encode() + b".evt1." + body, hashlib.sha256
    ).hexdigest()
    headers = {
        "X-CDIP-Timestamp": sent_at,
        "X-CDIP-Event-ID": "evt1",
        "X-CDIP-Signature": signature,
        "Content-Type": "application/json",
    }
    endpoint = f"/api/v1/webhooks/{source.id}"
    assert client.post(endpoint, content=body).status_code == 401
    result = client.post(endpoint, content=body, headers=headers)
    assert result.status_code == 202, result.text
    inbox_id = result.json()["inbox_id"]
    assert client.post(endpoint, content=body, headers=headers).json()["duplicate"] is True
    with Session(db) as session:
        assert session.get(Webhook, inbox_id).processed_at is None
        assert not session.scalars(select(Record)).all()
    ingestion = IngestionEngine(db, settings)
    ingestion.process_webhook(inbox_id)
    ingestion.process_webhook(inbox_id)
    with Session(db) as session:
        assert len(session.scalars(select(Record)).all()) == 1
        assert session.get(Webhook, inbox_id).processed_at is not None
    headers["X-CDIP-Event-ID"] = "tampered"
    assert client.post(endpoint, content=body, headers=headers).status_code == 401


def test_body_limit(db, settings):
    settings.request_limit_bytes = 100
    client = TestClient(create_app(settings, db))
    assert client.post("/api/v1/sources", content=b"x" * 101, headers=ADMIN).status_code == 413


def test_openapi_contract(db, settings):
    schema = create_app(settings, db).openapi()
    assert "/api/v1/sources/{source_id}/sync" in schema["paths"]
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
