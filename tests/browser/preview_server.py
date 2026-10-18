import threading
import time
from datetime import timedelta
from pathlib import Path

import uvicorn
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from apps.api.main import create_app
from commerce_data.config import Settings
from commerce_data.ingestion.engine import IngestionEngine
from commerce_data.storage.models import Base, Run, Source, SyncState, utcnow


def main():
    root = Path(".local/ui-fixtures").resolve()
    root.mkdir(parents=True, exist_ok=True)
    (root / "employees.csv").write_text("id,name\n1,Demo\n2,Demo 2\n", encoding="utf-8")
    settings = Settings(_env_file=None, csv_root=root)
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {"ops": None, "raw": None}},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as s, s.begin():
        for i, name in enumerate(
            ["Nhân viên cửa hàng", "Đơn hàng trực tuyến", "Danh mục sản phẩm"]
        ):
            source = Source(
                name=name,
                kind="csv",
                config={"kind": "csv", "path": "employees.csv", "key_field": "id"},
                enabled=i != 2,
                sync_interval_seconds=300,
            )
            s.add(source)
            s.flush()
            s.add(SyncState(source_id=source.id, last_success_at=utcnow() - timedelta(minutes=3)))
            s.add(
                Run(
                    source_id=source.id,
                    kind="sync",
                    status="failed" if i == 1 else "succeeded",
                    rows_inserted=2,
                )
            )

    def worker():
        while True:
            time.sleep(2)
            with Session(engine) as s:
                ids = list(s.scalars(select(Run.id).where(Run.status == "queued")))
            for rid in ids:
                IngestionEngine(engine, settings).run(rid)

    threading.Thread(target=worker, daemon=True).start()
    uvicorn.run(create_app(settings, engine), host="127.0.0.1", port=8010, access_log=False)


if __name__ == "__main__":
    main()
