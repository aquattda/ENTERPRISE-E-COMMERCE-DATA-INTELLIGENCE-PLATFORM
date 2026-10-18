import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from apps.api.main import create_app
from commerce_data.connectors.contracts import PostgresConfig
from commerce_data.connectors.postgres import PostgresConnector
from commerce_data.ingestion.engine import SourceBusy, enqueue, source_lock
from commerce_data.storage.models import Run
from tests.unit.test_api import (  # noqa: F401
    test_auth_validation_and_jobs,
    test_webhook_durable_idempotent_and_authenticated,
)
from tests.unit.test_ingestion import (  # noqa: F401
    test_backfill_does_not_rewind_live_cursor,
    test_commit_atomicity,
    test_enqueue_coalesces_and_running_job_recovery,
    test_resume_dedup_backfill_and_out_of_order,
    test_snapshot_changes_deletes_readd_and_reorder,
    test_snapshot_duplicate_keys_fail,
    test_source_shop_scope,
)
from tests.unit.test_profit import (  # noqa: F401
    test_business_api_cost_history_projection_export,
    test_invalid_business_data_blocks_verified_total,
    test_latest_version_not_double_counted_and_duplicate_source_blocked,
)
from tests.unit.test_ui import (  # noqa: F401
    test_csv_preview_import_and_worker_dedup,
    test_overview_latest_failure_paused_and_vietnam_day,
    test_shared_workspace_no_login_and_csrf,
)

pytestmark = pytest.mark.postgres


def test_health_and_database_privileges(db, settings):
    client = TestClient(create_app(settings, db))
    assert client.get("/api/v1/health").status_code == 200
    with db.connect() as conn:
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0002_cost_book"
        if conn.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='cdip_app')")):
            assert not conn.scalar(text("SELECT rolsuper FROM pg_roles WHERE rolname='cdip_app'"))
            assert not conn.scalar(
                text("SELECT has_table_privilege('cdip_app', 'raw.record_versions', 'DELETE')")
            )
            assert not conn.scalar(
                text("SELECT has_table_privilege('cdip_reader', 'raw.record_versions', 'SELECT')")
            )
            assert conn.scalar(
                text(
                    "SELECT has_table_privilege('cdip_reader', "
                    "'mart.pipeline_status_summary', 'SELECT')"
                )
            )


def test_source_lock_exclusion_and_release(db, source):
    with source_lock(db, source.id):
        with pytest.raises(SourceBusy), source_lock(db, source.id):
            pass
    with source_lock(db, source.id):
        pass


def test_concurrent_enqueue_coalesces(db, source):
    def submit():
        with Session(db) as session, session.begin():
            return enqueue(session, source.id).id

    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda _: submit(), range(8)))
    assert len(set(ids)) == 1
    with Session(db) as session:
        assert len(session.scalars(select(Run)).all()) == 1


def test_postgres_connector_keyset_readonly_and_resume(db, settings, monkeypatch):
    url = os.environ["CDIP_TEST_DATABASE_URL"]
    monkeypatch.setenv("CDIP_SECRET_TEST_PG", url)
    settings.allowed_db_hosts = db.url.host
    with db.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS public.connector_fixture"))
        conn.execute(
            text("""CREATE TABLE public.connector_fixture (
            id integer, shop_id text, updated_at timestamptz NOT NULL,
            gross_amount numeric(18,2), PRIMARY KEY (shop_id,id))""")
        )
        conn.execute(
            text("INSERT INTO public.connector_fixture VALUES (:id,:shop,:at,:amount)"),
            [
                {
                    "id": i % 3,
                    "shop": f"s{i // 3}",
                    "at": datetime(2026, 1, 1, tzinfo=UTC),
                    "amount": "123.45",
                }
                for i in range(6)
            ],
        )
    config = PostgresConfig(
        secret_ref="env:CDIP_SECRET_TEST_PG",
        table="connector_fixture",
        fields=["id", "shop_id", "updated_at", "gross_amount"],
        batch_size=2,
    )
    connector = PostgresConnector(config, settings)
    try:
        pages = list(connector.fetch_incremental({}))
        assert sum(len(p.records) for p in pages) == 6
        assert len({(r["shop_id"], r["id"]) for p in pages for r in p.records}) == 6
        resumed = list(connector.fetch_incremental(pages[0].cursor))
        assert sum(len(p.records) for p in resumed) == 4
        with connector.engine.connect() as conn:
            assert conn.scalar(text("SHOW transaction_read_only")) == "on"
        assert "gross_amount" in connector.discover_schema()
    finally:
        connector.close()
        with db.begin() as conn:
            conn.execute(text("DROP TABLE public.connector_fixture"))


def test_scheduler_due_and_disabled(db, source):
    from commerce_data.storage.models import Source
    from flows.scheduler import dispatch_due

    assert dispatch_due(db) == 1
    assert dispatch_due(db) == 0
    with Session(db) as session, session.begin():
        session.get(Source, source.id).enabled = False
    assert dispatch_due(db) == 0


def test_scheduled_reconciliation_uses_separate_job(db, source):
    from datetime import timedelta

    from commerce_data.storage.models import SyncState, utcnow
    from flows.scheduler import dispatch_due

    with Session(db) as session, session.begin():
        state = session.get(SyncState, source.id)
        state.next_reconcile_at = utcnow() - timedelta(seconds=1)
        state.next_sync_at = utcnow() + timedelta(hours=1)
    assert dispatch_due(db) == 1
    with Session(db) as session:
        assert session.scalar(select(Run)).kind == "reconcile"
