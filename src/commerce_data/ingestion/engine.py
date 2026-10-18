import hashlib
import json
from collections.abc import Callable
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from commerce_data.config import Settings
from commerce_data.connectors.base import Connector, ConnectorError, Page, timestamp
from commerce_data.connectors.contracts import CommonConfig, config_adapter
from commerce_data.connectors.factory import build_connector
from commerce_data.storage.models import (
    Audit,
    Batch,
    Checkpoint,
    Record,
    Run,
    SnapshotRow,
    Source,
    SyncState,
    Webhook,
    new_id,
    utcnow,
)


class SourceBusy(RuntimeError):
    pass


def json_default(value: Any) -> str:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError("Unsupported JSON value")


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=json_default,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalize(record: dict, config: CommonConfig) -> tuple[str, str, datetime | None, bool]:
    # Mapping is reserved for Silver; Bronze keeps the exact original field names.
    key = record.get(config.key_field)
    if key is None or isinstance(key, (dict, list, bool)) or not str(key).strip():
        raise ConnectorError("Missing or invalid business key")
    shop = record.get(config.shop_field) if config.shop_field else config.shop_key
    if shop is None or not str(shop).strip():
        raise ConnectorError("Missing shop key")
    if len(str(key)) > 240 or len(str(shop)) > 160:
        raise ConnectorError("Business key exceeds configured storage limits")
    updated = None
    if config.updated_field:
        if not record.get(config.updated_field):
            raise ConnectorError("Missing source timestamp")
        updated = timestamp(record[config.updated_field])
    deleted = record.get(config.deleted_field, False)
    if not isinstance(deleted, bool):
        raise ConnectorError("Tombstone flag must be boolean")
    return str(key), str(shop), updated, deleted


@contextmanager
def source_lock(engine: Engine, source_id: str):
    if engine.dialect.name != "postgresql":
        # SQLite is only used in single-process unit tests.
        yield
        return
    lock_id = int.from_bytes(hashlib.sha256(source_id.encode()).digest()[:8], "big", signed=True)
    with engine.connect() as connection:
        acquired = connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_id})
        connection.commit()
        if not acquired:
            raise SourceBusy("Source is already being processed")
        try:
            yield
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_id})
            connection.commit()


def enqueue(session: Session, source_id: str, kind: str = "sync", actor: str = "admin") -> Run:
    source = session.scalar(select(Source).where(Source.id == source_id).with_for_update())
    if not source:
        raise LookupError("Source not found")
    if not source.enabled:
        raise ValueError("Source is disabled")
    existing = session.scalar(
        select(Run).where(Run.source_id == source_id, Run.status.in_(["queued", "running"]))
    )
    if existing:
        return existing
    run = Run(source_id=source_id, kind=kind)
    session.add(run)
    session.flush()
    session.add(Audit(actor=actor, action=f"enqueue.{kind}", resource_id=run.id))
    return run


class IngestionEngine:
    def __init__(
        self,
        engine: Engine,
        settings: Settings,
        connector_factory: Callable[[dict, Settings], Connector] = build_connector,
        before_commit: Callable[[], None] | None = None,
    ):
        self.engine = engine
        self.settings = settings
        self.connector_factory = connector_factory
        self.before_commit = before_commit

    def commit_page(
        self, run_id: str, config: CommonConfig, page: Page, snapshot_generation: str | None = None
    ) -> None:
        with Session(self.engine) as session, session.begin():
            run = session.get(Run, run_id)
            assert run
            batch = Batch(source_id=run.source_id, run_id=run.id, row_count=len(page.records))
            session.add(batch)
            session.flush()
            values = []
            for original in page.records:
                payload = json.loads(canonical(original))
                key, shop, updated, deleted = normalize(payload, config)
                version_hash = digest(payload)
                if snapshot_generation:
                    snapshot_key = canonical([shop, key])
                    if len(snapshot_key) > 240:
                        raise ConnectorError("Snapshot business key exceeds storage limit")
                    row = session.get(SnapshotRow, (run.source_id, snapshot_key))
                    if row and row.generation == snapshot_generation:
                        raise ConnectorError("Duplicate business key in snapshot")
                    changed = not row or row.row_hash != version_hash
                    if not row:
                        row = SnapshotRow(source_id=run.source_id, business_key=snapshot_key)
                        session.add(row)
                    row.payload = payload
                    row.row_hash = version_hash
                    row.generation = snapshot_generation
                    session.flush()
                    if not changed:
                        continue
                    # Include generation to preserve delete/re-add cycles with identical content.
                    version_hash = digest([version_hash, snapshot_generation])
                values.append(
                    dict(
                        id=new_id(),
                        source_id=run.source_id,
                        batch_id=batch.id,
                        entity=config.entity,
                        shop_key=shop,
                        business_key=key,
                        version_hash=version_hash,
                        payload=payload,
                        source_updated_at=updated,
                        received_at=utcnow(),
                        deleted=deleted,
                    )
                )
            inserted = 0
            if values:
                insert = pg_insert if self.engine.dialect.name == "postgresql" else sqlite_insert
                statement = (
                    insert(Record)
                    .values(values)
                    .on_conflict_do_nothing(
                        index_elements=[
                            "source_id",
                            "entity",
                            "shop_key",
                            "business_key",
                            "version_hash",
                        ]
                    )
                    .returning(Record.id)
                )
                inserted = len(session.scalars(statement).all())
            run.rows_fetched += len(page.records)
            run.rows_inserted += inserted
            run.duplicates += len(page.records) - inserted
            run.cursor = json.loads(canonical(page.cursor))
            # Backfill/reconciliation maintain their own cursors and never rewind live state.
            if run.kind == "sync" and not snapshot_generation:
                state = session.get(SyncState, run.source_id)
                assert state
                state.cursor = run.cursor
            session.add(
                Checkpoint(
                    source_id=run.source_id, run_id=run.id, batch_id=batch.id, cursor=run.cursor
                )
            )
            if self.before_commit:
                self.before_commit()

    def finish_snapshot(self, run_id: str, config: CommonConfig, generation: str) -> None:
        # Bounded deletion batches; only called after complete, successful source enumeration.
        while True:
            with Session(self.engine) as session:
                run = session.get(Run, run_id)
                assert run
                rows = session.scalars(
                    select(SnapshotRow)
                    .where(
                        SnapshotRow.source_id == run.source_id, SnapshotRow.generation != generation
                    )
                    .limit(config.batch_size)
                ).all()
                if not rows:
                    return
                payloads = []
                keys = []
                for row in rows:
                    payloads.append({**row.payload, config.deleted_field: True})
                    keys.append(row.business_key)
            # Tombstones and snapshot removal are atomic in the same transaction below.
            with Session(self.engine) as session, session.begin():
                batch = Batch(source_id=run.source_id, run_id=run_id, row_count=len(payloads))
                session.add(batch)
                session.flush()
                for payload in payloads:
                    key, shop, updated, _ = normalize(payload, config)
                    session.add(
                        Record(
                            source_id=run.source_id,
                            batch_id=batch.id,
                            entity=config.entity,
                            shop_key=shop,
                            business_key=key,
                            payload=payload,
                            deleted=True,
                            source_updated_at=updated,
                            version_hash=digest([payload, generation]),
                        )
                    )
                session.execute(
                    delete(SnapshotRow).where(
                        SnapshotRow.source_id == run.source_id, SnapshotRow.business_key.in_(keys)
                    )
                )
                current_run = session.get(Run, run_id)
                assert current_run
                current_run.rows_inserted += len(payloads)
                if self.before_commit:
                    self.before_commit()

    def run(self, run_id: str) -> None:
        with Session(self.engine) as session:
            run = session.get(Run, run_id)
            if not run or run.status == "succeeded":
                return
            source_id = run.source_id
        with source_lock(self.engine, source_id):
            connector = None
            try:
                with Session(self.engine) as session, session.begin():
                    run = session.get(Run, run_id)
                    assert run
                    if run.status == "succeeded":
                        return
                    source = session.get(Source, source_id)
                    state = session.get(SyncState, source_id)
                    assert source and state
                    if not source.enabled:
                        raise ConnectorError("Source is disabled")
                    config_dict = source.config
                    sync_interval = source.sync_interval_seconds
                    config = config_adapter.validate_python(config_dict)
                    cursor = run.cursor or (state.cursor if run.kind == "sync" else {})
                    run.status = "running"
                    run.started_at = utcnow()
                    run.error_code = None
                connector = self.connector_factory(config_dict, self.settings)
                generation = new_id() if connector.capabilities.snapshot else None
                for page in connector.fetch_incremental({} if generation else cursor):
                    self.commit_page(run_id, config, page, generation)
                if generation:
                    self.finish_snapshot(run_id, config, generation)
                with Session(self.engine) as session, session.begin():
                    run = session.get(Run, run_id)
                    state = session.get(SyncState, source_id)
                    assert run and state
                    run.status = "succeeded"
                    run.finished_at = utcnow()
                    run.retries = connector.retries
                    run.rate_limits = connector.rate_limits
                    if run.kind == "sync":
                        state.last_success_at = utcnow()
                        state.next_sync_at = utcnow() + timedelta(seconds=sync_interval)
            except Exception as exc:
                with Session(self.engine) as session, session.begin():
                    run = session.get(Run, run_id)
                    assert run
                    run.status = "failed"
                    run.finished_at = utcnow()
                    # Exception messages may contain credentials, request data or PII.
                    run.error_code = type(exc).__name__
                    if connector:
                        run.retries = connector.retries
                        run.rate_limits = connector.rate_limits
                raise
            finally:
                if connector:
                    connector.close()

    def process_webhook(self, webhook_id: str) -> None:
        with Session(self.engine) as session:
            inbox = session.get(Webhook, webhook_id)
            if not inbox or inbox.processed_at:
                return
            source_id = inbox.source_id
        with source_lock(self.engine, source_id):
            with Session(self.engine) as session, session.begin():
                inbox = session.get(Webhook, webhook_id)
                source = session.get(Source, source_id)
                assert inbox and source
                if inbox.processed_at or not source.enabled:
                    return
                config = config_adapter.validate_python(source.config)
                # A generic webhook carries one record and shares REST content deduplication.
                key, shop, updated, deleted = normalize(inbox.payload, config)
                run = Run(
                    source_id=source_id,
                    kind="webhook",
                    status="succeeded",
                    started_at=utcnow(),
                    finished_at=utcnow(),
                    rows_fetched=1,
                )
                session.add(run)
                session.flush()
                batch = Batch(source_id=source_id, run_id=run.id, row_count=1)
                session.add(batch)
                session.flush()
                insert = pg_insert if self.engine.dialect.name == "postgresql" else sqlite_insert
                result = session.scalar(
                    insert(Record)
                    .values(
                        id=new_id(),
                        source_id=source_id,
                        batch_id=batch.id,
                        entity=config.entity,
                        shop_key=shop,
                        business_key=key,
                        payload=inbox.payload,
                        version_hash=digest(inbox.payload),
                        source_updated_at=updated,
                        deleted=deleted,
                    )
                    .on_conflict_do_nothing(
                        index_elements=[
                            "source_id",
                            "entity",
                            "shop_key",
                            "business_key",
                            "version_hash",
                        ]
                    )
                    .returning(Record.id)
                )
                run.rows_inserted = int(result is not None)
                run.duplicates = int(result is None)
                inbox.processed_at = utcnow()
