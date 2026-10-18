"""Synthetic Bronze benchmark. Never runs against a non-test database."""

import argparse
import json
import os
import platform
import statistics
import time

from sqlalchemy import create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from apps.mock_api.main import synthetic_record
from commerce_data.config import Settings
from commerce_data.connectors.base import Capabilities, Connector, Page
from commerce_data.connectors.contracts import RestConfig
from commerce_data.ingestion.engine import IngestionEngine, enqueue
from commerce_data.storage.models import Record, Source, SyncState, new_id

parser = argparse.ArgumentParser()
parser.add_argument("--rows", type=int, choices=[10000, 100000, 300000, 1000000], default=10000)
parser.add_argument("--batch-size", type=int, default=500)
args = parser.parse_args()
if not 1 <= args.batch_size <= 5000:
    raise SystemExit("Batch size must be between 1 and 5000")
url = os.environ["CDIP_TEST_DATABASE_URL"]
if not (make_url(url).database or "").endswith("_test"):
    raise SystemExit("Benchmark requires a disposable *_test database with migrations applied")


class Synthetic(Connector):
    capabilities = Capabilities(incremental=True)

    def fetch_incremental(self, cursor):
        for start in range(0, args.rows, args.batch_size):
            end = min(start + args.batch_size, args.rows)
            yield Page([synthetic_record(i) for i in range(start, end)], {"offset": end})


class MeasuredIngestion(IngestionEngine):
    latencies: list[float] = []

    def commit_page(self, *args, **kwargs):
        start = time.perf_counter()
        super().commit_page(*args, **kwargs)
        self.latencies.append(time.perf_counter() - start)


engine = create_engine(url)
with Session(engine, expire_on_commit=False) as session, session.begin():
    source = Source(
        name="benchmark-" + new_id(),
        kind="rest",
        config=RestConfig(
            base_url="https://synthetic.invalid", batch_size=args.batch_size
        ).model_dump(),
    )
    session.add(source)
    session.flush()
    session.add(SyncState(source_id=source.id))
    session.flush()
    job = enqueue(session, source.id)
    job_id = job.id
    source_id = source.id
measured = MeasuredIngestion(engine, Settings(_env_file=None), lambda *_: Synthetic())
start = time.perf_counter()
measured.run(job_id)
duration = time.perf_counter() - start
with Session(engine) as session:
    assert (
        session.scalar(
            select(func.count()).select_from(Record).where(Record.source_id == source_id)
        )
        == args.rows
    )
    replay = enqueue(session, source_id, "backfill")
    replay_id = replay.id
    session.commit()
replay_start = time.perf_counter()
measured.run(replay_id)
replay_duration = time.perf_counter() - replay_start
with Session(engine) as session:
    assert (
        session.scalar(
            select(func.count()).select_from(Record).where(Record.source_id == source_id)
        )
        == args.rows
    )
peak_rss_mib = None
if platform.system() == "Linux":
    import resource

    peak_rss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
print(
    json.dumps(
        {
            "scope": "synthetic connector -> Bronze PostgreSQL; no HTTP/KPI",
            "rows": args.rows,
            "batch_size": args.batch_size,
            "insert_seconds": duration,
            "rows_per_second": args.rows / duration,
            "idempotent_replay_seconds": replay_duration,
            "batch_p95_seconds_insert_and_replay": statistics.quantiles(measured.latencies, n=20)[
                18
            ],
            "process_peak_rss_mib": peak_rss_mib,
            "platform": platform.platform(),
        }
    )
)
engine.dispose()
