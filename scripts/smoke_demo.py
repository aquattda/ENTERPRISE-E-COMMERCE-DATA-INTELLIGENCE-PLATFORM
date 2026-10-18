"""Verify the seeded synthetic sources via live API and the application DB role."""

import json
import os
import time
from datetime import datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from commerce_data.storage.database import make_engine
from commerce_data.storage.models import Record, Source

headers = {"Authorization": "Bearer " + os.environ["CDIP_ADMIN_TOKEN"]}
with httpx.Client(base_url="http://localhost:8000", headers=headers, timeout=10) as client:
    client.get("/api/v1/health").raise_for_status()
    sources = client.get("/api/v1/sources").json()["items"]
    selected = [s for s in sources if s["name"].startswith("Synthetic ")]
    assert len(selected) == 2
    jobs = []
    for source in selected:
        response = client.post(f"/api/v1/sources/{source['id']}/sync")
        response.raise_for_status()
        jobs.append(response.json()["job_id"])
    deadline = time.monotonic() + 55
    for job in jobs:
        while True:
            run = client.get(f"/api/v1/pipelines/runs/{job}").json()
            if run["status"] == "failed":
                raise RuntimeError(run["error_code"])
            if run["status"] == "succeeded":
                assert run["rows_inserted"] == 0, "Unchanged replay inserted duplicates"
                duration = (
                    datetime.fromisoformat(run["finished_at"])
                    - datetime.fromisoformat(run["started_at"])
                ).total_seconds()
                print(
                    json.dumps(
                        {
                            "job_id": job,
                            "status": run["status"],
                            "rows_fetched": run["rows_fetched"],
                            "rows_inserted": run["rows_inserted"],
                            "duplicates": run["duplicates"],
                            "seconds": duration,
                        }
                    )
                )
                break
            if time.monotonic() > deadline:
                raise TimeoutError("Smoke job did not finish within 55 seconds")
            time.sleep(1)
engine = make_engine()
with Session(engine) as session:
    counts = dict(
        session.execute(
            select(Source.name, func.count(Record.id))
            .join(Record, Record.source_id == Source.id)
            .group_by(Source.name)
        )
        .tuples()
        .all()
    )
    assert counts["Synthetic commerce orders"] == 10000
    assert counts["Synthetic employees CSV"] == 3
    print(json.dumps({"verified_raw_counts": counts}))
engine.dispose()
