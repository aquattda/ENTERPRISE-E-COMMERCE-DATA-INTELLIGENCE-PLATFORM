import hashlib
import hmac
import json
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.business import install_business
from apps.api.ui import install_ui, source_context
from commerce_data.config import Settings, get_settings
from commerce_data.connectors.contracts import SourceConfig, config_adapter
from commerce_data.connectors.factory import build_connector
from commerce_data.ingestion.engine import digest, enqueue, normalize
from commerce_data.security import validate_url
from commerce_data.storage.database import make_engine
from commerce_data.storage.models import Audit, Record, Run, Source, SyncState, Webhook, utcnow
from commerce_data.web_auth import browser_session, role_for_token


class SourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    config: SourceConfig
    enabled: bool = True
    sync_interval_seconds: int = Field(default=120, ge=60, le=86400)


class SourcePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool | None = None
    reconciliation_interval_seconds: int | None = Field(default=None, ge=300, le=2592000)
    sync_interval_seconds: int | None = Field(default=None, ge=60, le=86400)


def create_app(settings: Settings | None = None, engine=None) -> FastAPI:
    settings = settings or get_settings()
    owns_engine = engine is None
    engine = engine or make_engine(settings.database_url.get_secret_value())

    @asynccontextmanager
    async def lifespan(app):
        yield
        if owns_engine:
            engine.dispose()

    app = FastAPI(title="Commerce Data Intelligence Platform", version="0.1.0", lifespan=lifespan)
    app.state.engine = engine
    bearer = HTTPBearer(auto_error=False)
    requests: dict[str, deque[float]] = defaultdict(deque)

    def session_dependency():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    def authorized(
        request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)
    ) -> str:
        if credentials:
            return role_for_token(credentials.credentials, settings)
        return str(browser_session(request, settings)["role"])

    def admin(role: str = Depends(authorized)) -> str:
        if role not in {"admin", "workspace"}:
            raise HTTPException(403, "Administrator role required")
        return role

    @app.middleware("http")
    async def limits(request: Request, call_next):
        # Bound request buffering even for chunked requests without Content-Length.
        body = bytearray()
        max_bytes = (
            settings.upload_limit_bytes
            if request.url.path.startswith("/api/v1/imports/csv")
            else settings.request_limit_bytes
        )
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > max_bytes:
                return JSONResponse({"error": {"code": "body_too_large"}}, status_code=413)
        request._body = bytes(body)
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = requests[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= 120:
            return JSONResponse(
                {"error": {"code": "rate_limited"}}, status_code=429, headers={"Retry-After": "60"}
            )
        bucket.append(now)
        if len(requests) > 10000:
            requests.clear()
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        elif request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(
            {"error": {"code": str(exc.status_code), "message": exc.detail}},
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            {
                "error": {
                    "code": "validation_error",
                    "fields": [
                        {"location": list(e["loc"]), "type": e["type"]} for e in exc.errors()
                    ],
                }
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception):
        return JSONResponse({"error": {"code": "internal_error"}}, status_code=500)

    def get_source(source_id: str, session: Session) -> Source:
        source = session.get(Source, source_id)
        if not source:
            raise HTTPException(404, "Source not found")
        return source

    @app.get("/api/v1/health", tags=["operations"])
    def health(session: Session = Depends(session_dependency)):
        try:
            session.execute(text("SELECT 1"))
            revision = session.scalar(text("SELECT version_num FROM public.alembic_version"))
            if revision != "0002_cost_book":
                raise RuntimeError("Migration required")
        except Exception:
            raise HTTPException(503, "Database unavailable or migration required") from None
        return {"status": "ok", "phase": "1-2", "version": "0.1.0"}

    @app.get("/api/v1/sources", dependencies=[Depends(authorized)], tags=["sources"])
    def list_sources(
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        q: str = Query("", max_length=120),
        kind: Literal["rest", "csv", "sheets", "postgres"] | None = None,
        session: Session = Depends(session_dependency),
    ):
        query = select(Source)
        if q:
            query = query.where(Source.name.icontains(q, autoescape=True))
        if kind:
            query = query.where(Source.kind == kind)
        items = session.scalars(
            query.order_by(Source.created_at, Source.id).offset(offset).limit(limit)
        ).all()
        return {
            "items": items,
            "limit": limit,
            "offset": offset,
            "total": session.scalar(select(func.count()).select_from(query.subquery())),
            "states": source_context(session, [source.id for source in items]),
        }

    @app.post("/api/v1/sources", status_code=201, tags=["sources"])
    def create_source(
        body: SourceCreate,
        actor: str = Depends(admin),
        session: Session = Depends(session_dependency),
    ):
        config = body.config.model_dump()
        if config["kind"] == "rest":
            try:
                validate_url(config["base_url"], settings.allowed_http_hosts, settings.allow_http)
                if config.get("token_url"):
                    validate_url(
                        config["token_url"], settings.allowed_http_hosts, settings.allow_http
                    )
            except ValueError:
                raise HTTPException(422, "Source URL is not allowed") from None
        source = Source(
            name=body.name,
            kind=config["kind"],
            config=config,
            enabled=body.enabled,
            sync_interval_seconds=body.sync_interval_seconds,
        )
        session.add(source)
        try:
            session.flush()
            session.add(
                SyncState(
                    source_id=source.id,
                    next_reconcile_at=utcnow()
                    + timedelta(seconds=body.config.reconciliation_interval_seconds),
                )
            )
            session.add(Audit(actor=actor, action="source.create", resource_id=source.id))
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, "Source name already exists") from None
        return source

    @app.get("/api/v1/sources/{source_id}", dependencies=[Depends(authorized)], tags=["sources"])
    def source_detail(source_id: str, session: Session = Depends(session_dependency)):
        source = get_source(source_id, session)
        return {"source": source, "sync_state": session.get(SyncState, source_id)}

    @app.patch("/api/v1/sources/{source_id}", tags=["sources"])
    def source_patch(
        source_id: str,
        body: SourcePatch,
        actor: str = Depends(admin),
        session: Session = Depends(session_dependency),
    ):
        source = get_source(source_id, session)
        state = session.get(SyncState, source_id)
        assert state
        for key, value in body.model_dump(exclude_none=True).items():
            if key == "reconciliation_interval_seconds":
                source.config = {**source.config, key: value}
                state.next_reconcile_at = utcnow() + timedelta(seconds=value)
            else:
                setattr(source, key, value)
                if key == "sync_interval_seconds":
                    state.next_sync_at = utcnow() + timedelta(seconds=value)
        session.add(Audit(actor=actor, action="source.update", resource_id=source_id))
        session.commit()
        return source

    def inspect_source(source_id: str, session: Session, sample: bool):
        source = get_source(source_id, session)
        connector = None
        try:
            connector = build_connector(source.config, settings)
            if sample:
                # Schema only, never expose raw sample/PII through this endpoint.
                result = {
                    "schema": connector.discover_schema(),
                    "statistics_scope": "sample",
                    "sample_limit": 100,
                    "quality_engine": "phase_3_pending",
                }
            else:
                result = {
                    "connected": connector.validate_connection(),
                    "capabilities": asdict(connector.capabilities),
                }
            session.add(Audit(actor="admin", action="source.inspect", resource_id=source_id))
            session.commit()
            return result
        except Exception:
            raise HTTPException(
                502, "Source inspection failed; check configuration and credentials"
            ) from None
        finally:
            if connector:
                connector.close()

    @app.post("/api/v1/sources/{source_id}/test", dependencies=[Depends(admin)], tags=["sources"])
    def test_source(source_id: str, session: Session = Depends(session_dependency)):
        return inspect_source(source_id, session, False)

    @app.post(
        "/api/v1/sources/{source_id}/profile", dependencies=[Depends(admin)], tags=["sources"]
    )
    def profile_source(source_id: str, session: Session = Depends(session_dependency)):
        return inspect_source(source_id, session, True)

    def queue(source_id: str, kind: str, session: Session):
        get_source(source_id, session)
        try:
            run = enqueue(session, source_id, kind)
            session.commit()
        except ValueError:
            raise HTTPException(409, "Source is disabled") from None
        return {"job_id": run.id, "status": run.status, "kind": run.kind}

    @app.post(
        "/api/v1/sources/{source_id}/sync",
        status_code=202,
        dependencies=[Depends(admin)],
        tags=["pipelines"],
    )
    def sync(source_id: str, session: Session = Depends(session_dependency)):
        return queue(source_id, "sync", session)

    @app.post(
        "/api/v1/pipelines/{source_id}/backfill",
        status_code=202,
        dependencies=[Depends(admin)],
        tags=["pipelines"],
    )
    def backfill(source_id: str, session: Session = Depends(session_dependency)):
        return queue(source_id, "backfill", session)

    @app.post(
        "/api/v1/pipelines/{source_id}/reconcile",
        status_code=202,
        dependencies=[Depends(admin)],
        tags=["pipelines"],
    )
    def reconcile(source_id: str, session: Session = Depends(session_dependency)):
        return queue(source_id, "reconcile", session)

    @app.get("/api/v1/pipelines/runs", dependencies=[Depends(authorized)], tags=["pipelines"])
    def runs(
        source_id: str | None = None,
        status: Literal["queued", "running", "failed", "succeeded"] | None = None,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
        session: Session = Depends(session_dependency),
    ):
        query = select(Run)
        if source_id:
            query = query.where(Run.source_id == source_id)
        if status:
            query = query.where(Run.status == status)
        return {
            "items": session.scalars(
                query.order_by(Run.created_at.desc(), Run.id).limit(limit).offset(offset)
            ).all(),
            "limit": limit,
            "offset": offset,
            "total": session.scalar(select(func.count()).select_from(query.subquery())),
            "source_names": dict(session.execute(select(Source.id, Source.name)).tuples().all()),
        }

    @app.get(
        "/api/v1/pipelines/runs/{run_id}", dependencies=[Depends(authorized)], tags=["pipelines"]
    )
    def run_detail(run_id: str, session: Session = Depends(session_dependency)):
        run = session.get(Run, run_id)
        if not run:
            raise HTTPException(404, "Run not found")
        return run

    @app.get("/api/v1/metrics", dependencies=[Depends(authorized)], tags=["operations"])
    def metrics(session: Session = Depends(session_dependency)):
        return {
            "runs_by_status": {
                status: count
                for status, count in session.execute(
                    select(Run.status, func.count()).group_by(Run.status)
                ).all()
            },
            "raw_versions": session.scalar(select(func.count()).select_from(Record)),
            "sources": session.scalar(select(func.count()).select_from(Source)),
        }

    @app.post("/api/v1/webhooks/{source_id}", status_code=202, tags=["webhooks"])
    async def webhook(
        source_id: str, request: Request, session: Session = Depends(session_dependency)
    ):
        from commerce_data.security import secret_value

        source = get_source(source_id, session)
        if not source.enabled or source.kind != "rest":
            raise HTTPException(409, "Webhook is not enabled for this source")
        config = config_adapter.validate_python(source.config)
        try:
            secret = secret_value(config.webhook_secret_ref)
        except ValueError:
            raise HTTPException(503, "Webhook authentication is not configured") from None
        event_id = request.headers.get("X-CDIP-Event-ID", "")
        sent_at = request.headers.get("X-CDIP-Timestamp", "")
        signature = request.headers.get("X-CDIP-Signature", "")
        try:
            valid_time = abs(time.time() - int(sent_at)) <= settings.webhook_max_age_seconds
        except ValueError:
            valid_time = False
        if not valid_time or not 1 <= len(event_id) <= 160 or "\n" in event_id:
            raise HTTPException(401, "Invalid webhook envelope")
        body = await request.body()
        signed = sent_at.encode() + b"." + event_id.encode() + b"." + body
        expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(401, "Invalid webhook signature")
        try:
            payload = json.loads(body, parse_float=Decimal)
            # Serialize decimals losslessly for PostgreSQL JSONB.
            from commerce_data.ingestion.engine import canonical

            payload = json.loads(canonical(payload))
            if not isinstance(payload, dict):
                raise ValueError("Object required")
            normalize(payload, config)
            payload_hash = digest(payload)
        except (ValueError, TypeError, RuntimeError):
            raise HTTPException(422, "Invalid webhook record") from None
        inbox = Webhook(
            source_id=source_id, event_id=event_id, payload=payload, payload_hash=payload_hash
        )
        session.add(inbox)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            prior = session.scalar(
                select(Webhook).where(Webhook.source_id == source_id, Webhook.event_id == event_id)
            )
            if not prior or prior.payload_hash != payload_hash:
                raise HTTPException(409, "Event ID reused with different content") from None
            return {"inbox_id": prior.id, "duplicate": True}
        return {"inbox_id": inbox.id, "duplicate": False}

    @app.post("/api/v1/ai/analyze", dependencies=[Depends(authorized)], tags=["future phases"])
    def ai_not_configured():
        raise HTTPException(503, "AI is not configured; Phase 6 has not been implemented")

    install_business(app, authorized, admin, session_dependency)
    install_ui(app, settings, authorized, admin, session_dependency)
    return app


app = create_app()
