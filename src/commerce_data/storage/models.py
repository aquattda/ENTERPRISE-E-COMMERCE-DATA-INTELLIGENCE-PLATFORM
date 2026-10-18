"""Phase 1/2 schema. JSONB in PostgreSQL; SQLite variant only for fast unit tests."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


json_type = JSON().with_variant(JSONB(), "postgresql")


class Source(Base):
    __tablename__ = "source_system"
    __table_args__ = {"schema": "ops"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[str] = mapped_column(String(30))
    config: Mapped[dict[str, Any]] = mapped_column(json_type)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sync_interval_seconds: Mapped[int] = mapped_column(Integer, default=120)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SyncState(Base):
    __tablename__ = "sync_state"
    __table_args__ = {"schema": "ops"}
    source_id: Mapped[str] = mapped_column(ForeignKey("ops.source_system.id"), primary_key=True)
    cursor: Mapped[dict[str, Any]] = mapped_column(json_type, default=dict)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_sync_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    next_reconcile_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: utcnow() + timedelta(days=1)
    )


class Run(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (Index("ix_runs_status_created", "status", "created_at"), {"schema": "ops"})
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("ops.source_system.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="sync")
    status: Mapped[str] = mapped_column(String(20), default="queued")
    cursor: Mapped[dict[str, Any]] = mapped_column(json_type, default=dict)
    rows_fetched: Mapped[int] = mapped_column(Integer, default=0)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    rate_limits: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Batch(Base):
    __tablename__ = "ingestion_batches"
    __table_args__ = {"schema": "raw"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("ops.sync_runs.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("ops.source_system.id"))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    row_count: Mapped[int] = mapped_column(Integer)


class Record(Base):
    __tablename__ = "record_versions"
    __table_args__ = (
        UniqueConstraint("source_id", "entity", "shop_key", "business_key", "version_hash"),
        Index("ix_record_identity", "source_id", "entity", "shop_key", "business_key"),
        {"schema": "raw"},
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("ops.source_system.id"))
    batch_id: Mapped[str] = mapped_column(ForeignKey("raw.ingestion_batches.id"))
    entity: Mapped[str] = mapped_column(String(80))
    shop_key: Mapped[str] = mapped_column(String(160))
    business_key: Mapped[str] = mapped_column(String(240))
    version_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(json_type)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class Checkpoint(Base):
    __tablename__ = "sync_checkpoints"
    __table_args__ = {"schema": "ops"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("ops.source_system.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("ops.sync_runs.id"))
    batch_id: Mapped[str] = mapped_column(ForeignKey("raw.ingestion_batches.id"), unique=True)
    cursor: Mapped[dict[str, Any]] = mapped_column(json_type)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SnapshotRow(Base):
    __tablename__ = "snapshot_rows"
    __table_args__ = {"schema": "ops"}
    source_id: Mapped[str] = mapped_column(ForeignKey("ops.source_system.id"), primary_key=True)
    business_key: Mapped[str] = mapped_column(String(240), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(json_type)
    row_hash: Mapped[str] = mapped_column(String(64))
    generation: Mapped[str] = mapped_column(String(36), index=True)


class Webhook(Base):
    __tablename__ = "webhook_inbox"
    __table_args__ = (UniqueConstraint("source_id", "event_id"), {"schema": "ops"})
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("ops.source_system.id"))
    event_id: Mapped[str] = mapped_column(String(160))
    payload: Mapped[dict[str, Any]] = mapped_column(json_type)
    payload_hash: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Audit(Base):
    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "ops"}
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(36))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SkuCost(Base):
    """Append-only cost revisions; latest revision per effective date is authoritative."""

    __tablename__ = "sku_cost_book"
    __table_args__ = (
        Index("ix_cost_lookup", "shop_id", "sku", "currency", "effective_from"),
        {"schema": "ops"},
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sku: Mapped[str] = mapped_column(String(160))
    shop_id: Mapped[str] = mapped_column(String(160), default="*")
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    effective_from: Mapped[date] = mapped_column(Date)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(24, 6))
    note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
