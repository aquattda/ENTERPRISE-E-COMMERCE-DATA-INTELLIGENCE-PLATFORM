import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from commerce_data.connectors.base import Capabilities, Connector, ConnectorError, Page
from commerce_data.connectors.contracts import CsvConfig
from commerce_data.ingestion.engine import IngestionEngine, enqueue
from commerce_data.storage.models import Batch, Checkpoint, Record, Run, Source, SyncState
from tests.unit.test_connectors import record


class FakeConnector(Connector):
    def __init__(self, pages, snapshot=False, fail=False):
        self.pages = pages
        self.capabilities = Capabilities(incremental=not snapshot, snapshot=snapshot)
        self.fail = fail
        self.seen_cursor = None

    def fetch_incremental(self, cursor):
        self.seen_cursor = cursor
        yield from self.pages
        if self.fail:
            raise ConnectorError("simulated transport interruption")


def queued(db, source, kind="sync"):
    with Session(db, expire_on_commit=False) as session, session.begin():
        return enqueue(session, source.id, kind).id


def count(db, model):
    with Session(db) as session:
        return session.scalar(select(func.count()).select_from(model))


def test_commit_atomicity(db, source, settings):
    job = queued(db, source)
    conn = FakeConnector([Page([record(1)], {"page": "2"})])

    def crash():
        raise RuntimeError("crash before COMMIT")

    ingestion = IngestionEngine(db, settings, lambda *_: conn, crash)
    with pytest.raises(RuntimeError):
        ingestion.run(job)
    assert count(db, Record) == count(db, Batch) == count(db, Checkpoint) == 0
    with Session(db) as session:
        assert session.get(SyncState, source.id).cursor == {}
        assert session.get(Run, job).status == "failed"


def test_resume_dedup_backfill_and_out_of_order(db, source, settings):
    job = queued(db, source)
    first = FakeConnector([Page([record(1)], {"page": "2"})], fail=True)
    with pytest.raises(ConnectorError):
        IngestionEngine(db, settings, lambda *_: first).run(job)
    assert count(db, Record) == 1
    second = FakeConnector([Page([record(1), record(2)], {"watermark": "2026-01-01T00:00:00Z"})])
    IngestionEngine(db, settings, lambda *_: second).run(queued(db, source))
    assert second.seen_cursor == {"page": "2"}
    assert count(db, Record) == 2
    for _ in range(2):
        IngestionEngine(db, settings, lambda *_: second).run(queued(db, source, "backfill"))
    assert count(db, Record) == 2
    older = record(1, "2025-12-01T00:00:00Z")
    IngestionEngine(db, settings, lambda *_: FakeConnector([Page([older])])).run(queued(db, source))
    with Session(db) as session:
        versions = session.scalars(
            select(Record)
            .where(Record.business_key == "1")
            .order_by(Record.source_updated_at.desc())
        ).all()
        assert len(versions) == 2
        assert versions[0].payload["updated_at"] == "2026-01-01T00:00:00Z"
    # Bronze preserves both versions; Silver conflict resolution is a later phase.


def test_source_shop_scope(db, source, settings):
    other_shop = {**record(1), "shop_id": "s2"}
    conn = FakeConnector([Page([record(1), record(1), other_shop])])
    IngestionEngine(db, settings, lambda *_: conn).run(queued(db, source))
    assert count(db, Record) == 2


def test_snapshot_changes_deletes_readd_and_reorder(db, source, settings):
    with Session(db) as session, session.begin():
        session.get(Source, source.id).config = CsvConfig(path="unused.csv").model_dump()

    def run(rows, fail=False):
        conn = FakeConnector([Page(rows)], snapshot=True, fail=fail)
        IngestionEngine(db, settings, lambda *_: conn).run(queued(db, source))

    run([{"id": "1", "name": "a"}, {"id": "2", "name": "b"}])
    run([{"id": "2", "name": "b"}, {"id": "1", "name": "a"}])
    assert count(db, Record) == 2
    with pytest.raises(ConnectorError):
        run([{"id": "1", "name": "changed"}], fail=True)
    with Session(db) as session:
        assert not session.scalars(select(Record).where(Record.deleted.is_(True))).all()
    run([{"id": "1", "name": "changed"}])
    run([{"id": "1", "name": "changed"}, {"id": "2", "name": "b"}])
    with Session(db) as session:
        versions = session.scalars(
            select(Record).where(Record.business_key == "2").order_by(Record.received_at)
        ).all()
        assert [v.deleted for v in versions] == [False, True, False]


def test_snapshot_duplicate_keys_fail(db, source, settings):
    with Session(db) as session, session.begin():
        session.get(Source, source.id).config = CsvConfig(path="unused.csv").model_dump()
    conn = FakeConnector([Page([{"id": "1"}, {"id": "1"}])], snapshot=True)
    with pytest.raises(ConnectorError, match="Duplicate"):
        IngestionEngine(db, settings, lambda *_: conn).run(queued(db, source))
    assert count(db, Record) == 0


def test_backfill_does_not_rewind_live_cursor(db, source, settings):
    with Session(db) as session, session.begin():
        session.get(SyncState, source.id).cursor = {"watermark": "2026-01-02T00:00:00Z"}
    conn = FakeConnector([Page([record(1)], {"watermark": "2026-01-01T00:00:00Z"})])
    IngestionEngine(db, settings, lambda *_: conn).run(queued(db, source, "backfill"))
    assert conn.seen_cursor == {}
    with Session(db) as session:
        assert session.get(SyncState, source.id).cursor["watermark"] == "2026-01-02T00:00:00Z"


def test_enqueue_coalesces_and_running_job_recovery(db, source, settings):
    first = queued(db, source)
    assert queued(db, source) == first
    with Session(db) as session, session.begin():
        session.get(Run, first).status = "running"
    conn = FakeConnector([Page([record(1)])])
    IngestionEngine(db, settings, lambda *_: conn).run(first)
    IngestionEngine(db, settings, lambda *_: conn).run(first)
    assert count(db, Record) == 1


def test_worker_logs_error_code_without_secret(db, source, settings, caplog):
    from apps.worker.main import work_once

    job = queued(db, source)

    def bad_factory(*args):
        raise RuntimeError("PASSWORD-MUST-NEVER-APPEAR")

    work_once(IngestionEngine(db, settings, bad_factory))
    assert "PASSWORD-MUST-NEVER-APPEAR" not in caplog.text
    assert "RuntimeError" in caplog.text
    with Session(db) as session:
        assert session.get(Run, job).error_code == "RuntimeError"
