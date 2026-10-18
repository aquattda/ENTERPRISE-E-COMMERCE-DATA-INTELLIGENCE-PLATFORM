"""Destructive migration roundtrip limited to explicitly configured *_test database."""

import os

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from commerce_data.config import get_settings

url = os.environ["CDIP_TEST_DATABASE_URL"]
if not (make_url(url).database or "").endswith("_test"):
    raise SystemExit("Refusing migration roundtrip outside disposable *_test database")
os.environ["CDIP_DATABASE_URL"] = url
get_settings.cache_clear()
config = Config("alembic.ini")
command.downgrade(config, "base")
command.upgrade(config, "head")
print("Migration downgrade/upgrade roundtrip passed on disposable test database")
