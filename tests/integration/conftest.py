import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from commerce_data.config import get_settings
from commerce_data.storage.models import Base


@pytest.fixture(scope="session")
def migrated_engine():
    url = os.environ.get("CDIP_TEST_DATABASE_URL")
    if not url:
        pytest.skip("CDIP_TEST_DATABASE_URL is not set; PostgreSQL test not run")
    parsed = make_url(url)
    if not parsed.database or not parsed.database.endswith("_test"):
        raise RuntimeError("Integration tests only run against a disposable *_test database")
    previous = os.environ.get("CDIP_DATABASE_URL")
    os.environ["CDIP_DATABASE_URL"] = url
    get_settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(url, pool_size=5, max_overflow=5)
    yield engine
    engine.dispose()
    if previous is None:
        os.environ.pop("CDIP_DATABASE_URL", None)
    else:
        os.environ["CDIP_DATABASE_URL"] = previous
    get_settings.cache_clear()


@pytest.fixture
def db(migrated_engine):
    # This truncation is restricted above to an explicitly configured disposable test database.
    names = ", ".join(f'"{t.schema}"."{t.name}"' for t in Base.metadata.sorted_tables)
    with migrated_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} CASCADE"))
    return migrated_engine
