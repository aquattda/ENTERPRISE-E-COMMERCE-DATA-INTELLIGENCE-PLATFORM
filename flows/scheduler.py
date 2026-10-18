from datetime import timedelta

from prefect import flow
from sqlalchemy import select
from sqlalchemy.orm import Session

from commerce_data.config import get_settings
from commerce_data.ingestion.engine import enqueue
from commerce_data.storage.database import make_engine
from commerce_data.storage.models import Source, SyncState, utcnow


def dispatch_due(engine) -> int:
    count = 0
    with Session(engine) as session, session.begin():
        now = utcnow()
        sources = session.scalars(
            select(Source)
            .join(SyncState)
            .where(
                Source.enabled.is_(True),
                (SyncState.next_sync_at <= now) | (SyncState.next_reconcile_at <= now),
            )
            .with_for_update(skip_locked=True, of=Source)
        ).all()
        for source in sources:
            state = session.get(SyncState, source.id)
            assert state
            kind = "reconcile" if state.next_reconcile_at <= now else "sync"
            run = enqueue(session, source.id, kind, actor="scheduler")
            if run.kind != kind:
                continue
            if kind == "reconcile":
                interval = source.config.get("reconciliation_interval_seconds", 86400)
                state.next_reconcile_at = now + timedelta(seconds=interval)
            else:
                state.next_sync_at = now + timedelta(seconds=source.sync_interval_seconds)
            count += 1
    return count


@flow(name="cdip-dispatch", log_prints=False, persist_result=False)
def dispatch() -> int:
    engine = make_engine()
    try:
        return dispatch_due(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    dispatch.serve(
        name="source-schedules",
        interval=get_settings().dispatch_seconds,
        limit=1,
        pause_on_shutdown=False,
    )
