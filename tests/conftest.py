import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from commerce_data.config import Settings
from commerce_data.connectors.contracts import RestConfig
from commerce_data.storage.models import Base, Source, SyncState


@pytest.fixture
def settings(tmp_path):
    return Settings(
        _env_file=None,
        admin_token="test-admin",
        reader_token="test-reader",
        allowed_http_hosts="mock.test,sheets.googleapis.com",
        allow_http=True,
        csv_root=tmp_path,
    )


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": {"ops": None, "raw": None}},
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def source(db):
    with Session(db, expire_on_commit=False) as session, session.begin():
        source = Source(
            name="test", kind="rest", config=RestConfig(base_url="https://mock.test").model_dump()
        )
        session.add(source)
        session.flush()
        session.add(SyncState(source_id=source.id))
    return source
