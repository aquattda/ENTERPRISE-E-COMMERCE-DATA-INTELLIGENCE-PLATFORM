import json
import logging
import time
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from commerce_data.config import get_settings
from commerce_data.ingestion.engine import IngestionEngine, SourceBusy
from commerce_data.storage.database import make_engine
from commerce_data.storage.models import Run, Webhook

logger = logging.getLogger("cdip.worker")


def work_once(ingestion: IngestionEngine) -> int:
    with Session(ingestion.engine) as session:
        run_ids = session.scalars(
            select(Run.id)
            .where(Run.status.in_(["queued", "running"]))
            .order_by(Run.created_at)
            .limit(100)
        ).all()
        webhook_ids = session.scalars(
            select(Webhook.id)
            .where(Webhook.processed_at.is_(None))
            .order_by(Webhook.received_at)
            .limit(100)
        ).all()
    for resource_id, operation in [
        *((r, ingestion.run) for r in run_ids),
        *((w, ingestion.process_webhook) for w in webhook_ids),
    ]:
        try:
            operation(resource_id)
        except SourceBusy:
            continue
        except Exception as exc:
            logger.error(
                json.dumps(
                    {"event": "job_failed", "id": resource_id, "error_code": type(exc).__name__}
                )
            )
    return len(run_ids) + len(webhook_ids)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # HTTP libraries can log full request URLs; application logs only identifiers/codes.
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    settings = get_settings()
    ingestion = IngestionEngine(make_engine(), settings)
    while True:
        try:
            work_once(ingestion)
            Path("/tmp/cdip-worker-heartbeat").touch()
        except Exception as exc:
            logger.error(json.dumps({"event": "worker_failed", "error_code": type(exc).__name__}))
        time.sleep(settings.poll_seconds)


if __name__ == "__main__":
    main()
