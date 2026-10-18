"""Task-oriented browser API and local application assets."""

import csv
import io
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from commerce_data.config import Settings
from commerce_data.connectors.contracts import CsvConfig, SheetsConfig
from commerce_data.connectors.snapshot import SheetsConnector
from commerce_data.ingestion.engine import enqueue
from commerce_data.storage.models import Audit, Record, Run, Source, SyncState, new_id, utcnow
from commerce_data.web_auth import (
    COOKIE,
    LIFETIME,
    browser_session,
    issue_session,
)

ASSETS = Path(__file__).parent / "static"


def source_context(session: Session, source_ids: list[str]) -> dict:
    if not source_ids:
        return {}
    ranked = (
        select(
            Run.id,
            func.row_number()
            .over(partition_by=Run.source_id, order_by=(Run.created_at.desc(), Run.id.desc()))
            .label("rank"),
        )
        .where(Run.source_id.in_(source_ids))
        .subquery()
    )
    runs = session.scalars(
        select(Run).join(ranked, ranked.c.id == Run.id).where(ranked.c.rank == 1)
    ).all()
    states = session.scalars(select(SyncState).where(SyncState.source_id.in_(source_ids))).all()
    result: dict[str, dict[str, Any]] = {
        sid: {"last_success_at": None, "next_sync_at": None, "latest_run": None}
        for sid in source_ids
    }
    for state in states:
        result[state.source_id].update(
            last_success_at=state.last_success_at, next_sync_at=state.next_sync_at
        )
    for run in runs:
        result[run.source_id]["latest_run"] = run
    return result


def csv_rows(body: bytes) -> tuple[list[str], list[list[str]], str]:
    try:
        decoded = body.decode("utf-8-sig", errors="strict")
        if "\x00" in decoded:
            raise ValueError()
        try:
            delimiter = csv.Sniffer().sniff(decoded[:8192], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
        reader = csv.reader(io.StringIO(decoded, newline=""), delimiter=delimiter, strict=True)
        headers = next(reader, [])
        if not headers or len(headers) > 50 or any(not h.strip() for h in headers):
            raise HTTPException(422, "csv_headers")
        if len(set(headers)) != len(headers):
            raise HTTPException(422, "csv_duplicate_headers")
        rows = []
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) != len(headers):
                raise HTTPException(422, "csv_width")
            rows.append(row)
            if len(rows) > 100000:
                raise HTTPException(422, "csv_row_limit")
        if not rows:
            raise HTTPException(422, "csv_empty")
        return headers, rows, delimiter
    except (UnicodeError, csv.Error, ValueError):
        raise HTTPException(422, "csv_encoding") from None


def install_ui(app: FastAPI, settings: Settings, authorized, admin, session_dependency) -> None:
    app.mount("/assets", StaticFiles(directory=ASSETS), name="ui-assets")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(
            ASSETS / "index.html",
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
                "Referrer-Policy": "same-origin",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get("/api/v1/session", tags=["browser"])
    def workspace_session(request: Request, response: Response):
        # The internal workspace is shared: no user accounts or role selection.
        origin = request.headers.get("Origin")
        if (origin and origin.rstrip("/") != str(request.base_url).rstrip("/")) or (
            request.headers.get("Sec-Fetch-Site") == "cross-site"
        ):
            raise HTTPException(403, "Invalid browser request")
        try:
            data = browser_session(request, settings)
            if data["role"] == "workspace":
                return data
        except HTTPException:
            pass
        cookie, data = issue_session("workspace", settings)
        response.set_cookie(
            COOKIE,
            cookie,
            max_age=LIFETIME,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="strict",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return data

    @app.get("/api/v1/overview", dependencies=[Depends(authorized)], tags=["browser"])
    def overview(session: Session = Depends(session_dependency)):
        sources = session.scalars(select(Source).order_by(Source.name)).all()
        context = source_context(session, [s.id for s in sources])
        attention = []
        active = 0
        updated = 0
        now = utcnow()
        for source in sources:
            state = context[source.id]
            run = state["latest_run"]
            last_success = state["last_success_at"]
            if last_success:
                updated += 1
            if not source.enabled:
                continue
            active += 1
            reason = None
            if run and run.status == "failed":
                reason = "failed"
            elif last_success and (now - last_success.replace(tzinfo=UTC)).total_seconds() > max(
                source.sync_interval_seconds * 3, 900
            ):
                reason = "delayed"
            if reason:
                attention.append({"source_id": source.id, "name": source.name, "reason": reason})
        local_now = now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        since = datetime.combine(
            local_now.date(), datetime.min.time(), tzinfo=local_now.tzinfo
        ).astimezone(UTC)
        today = dict(
            session.execute(
                select(Run.status, func.count()).where(Run.created_at >= since).group_by(Run.status)
            )
            .tuples()
            .all()
        )
        latest = session.scalar(select(func.max(SyncState.last_success_at)))
        return {
            "source_count": len(sources),
            "sample_source_count": sum(
                source.config.get("base_url") == "http://mock-api:9000"
                or (source.kind == "csv" and source.config.get("path") == "employees.csv")
                for source in sources
            ),
            "active_sources": active,
            "updated_sources": updated,
            "raw_versions": session.scalar(select(func.count()).select_from(Record)),
            "attention_count": len(attention),
            "attention": attention[:5],
            "runs_today": today,
            "day_timezone": "Asia/Ho_Chi_Minh",
            "last_success_at": latest,
            "generated_at": now,
        }

    @app.get("/api/v1/connections", dependencies=[Depends(admin)], tags=["browser"])
    def connections():
        # Expose names only, never secret values; only Google credentials used by this form.
        return {
            "google": [
                f"env:{key}"
                for key in sorted(os.environ)
                if key.startswith("CDIP_SECRET_GOOGLE") and os.environ[key]
            ]
        }

    @app.post("/api/v1/connections/sheets/test", dependencies=[Depends(admin)], tags=["browser"])
    def check_sheets(config: SheetsConfig):
        connector = SheetsConnector(config, settings)
        try:
            columns = list(connector.discover_schema())
            if config.key_field not in columns:
                raise HTTPException(422, "sheets_key_missing")
            return {"connected": True, "columns": columns}
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(502, "sheets_connection_failed") from None
        finally:
            connector.close()

    @app.post("/api/v1/imports/csv/preview", dependencies=[Depends(admin)], tags=["browser"])
    async def preview_csv(request: Request):
        headers, rows, delimiter = csv_rows(await request.body())
        suggested = next(
            (
                h
                for h in headers
                if h.lower()
                in {"id", "employee_id", "order_id", "product_id", "ma_nhan_vien", "ma_don_hang"}
            ),
            headers[0],
        )
        return {
            "headers": headers,
            "sample": rows[:5],
            "row_count": len(rows),
            "suggested_key": suggested,
            "delimiter": delimiter,
        }

    @app.post("/api/v1/imports/csv", status_code=201, tags=["browser"])
    async def import_csv(
        request: Request,
        name: str = Query(min_length=1, max_length=120),
        key_field: str = Query(min_length=1, max_length=240),
        actor: str = Depends(admin),
        session: Session = Depends(session_dependency),
    ):
        body = await request.body()
        headers, rows, delimiter = csv_rows(body)
        if key_field not in headers:
            raise HTTPException(422, "csv_key_missing")
        index = headers.index(key_field)
        keys = [row[index] for row in rows]
        if any(not key.strip() or len(key) > 200 for key in keys):
            raise HTTPException(422, "csv_key_empty")
        if len(set(keys)) != len(keys):
            raise HTTPException(422, "csv_key_duplicate")
        if session.scalar(select(Source.id).where(Source.name == name)):
            raise HTTPException(409, "Source name already exists")
        upload_dir = settings.csv_root.resolve() / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = new_id() + ".csv"
        path = upload_dir / filename
        config = CsvConfig(
            path="uploads/" + filename,
            key_field=key_field,
            delimiter=cast(Literal[",", ";", "\t", "|"], delimiter),
            entity="imported_records",
        ).model_dump()
        source = Source(name=name, kind="csv", config=config, sync_interval_seconds=300)
        created_file = False
        try:
            with path.open("xb") as handle:
                handle.write(body)
            created_file = True
            session.add(source)
            session.flush()
            session.add(SyncState(source_id=source.id))
            session.add(Audit(actor=actor, action="source.csv_upload", resource_id=source.id))
            session.flush()
            job = enqueue(session, source.id, actor=actor)
            session.commit()
        except Exception as exc:
            session.rollback()
            if created_file:
                path.unlink(missing_ok=True)
            if isinstance(exc, IntegrityError):
                raise HTTPException(409, "Source name already exists") from None
            raise
        return {"source_id": source.id, "job_id": job.id, "row_count": len(rows)}
