from collections.abc import Iterator
from datetime import timedelta
from typing import Any

from sqlalchemy import MetaData, Table, and_, create_engine, inspect, or_, select, text
from sqlalchemy.engine import make_url

from commerce_data.config import Settings
from commerce_data.connectors.base import Capabilities, Connector, Page, timestamp
from commerce_data.connectors.contracts import PostgresConfig
from commerce_data.security import ConfigurationError, secret_value


class PostgresConnector(Connector):
    capabilities = Capabilities(incremental=True, field_selection=True)

    def __init__(self, config: PostgresConfig, settings: Settings):
        self.config = config
        url = make_url(secret_value(config.secret_ref))
        if (
            url.drivername != "postgresql+psycopg"
            or url.host not in settings.allowed_db_hosts.split(",")
        ):
            raise ConfigurationError("Source database must be PostgreSQL on an allowed host")
        self.engine = create_engine(
            url,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
            connect_args={
                "connect_timeout": 10,
                "options": f"-c default_transaction_read_only=on "
                f"-c statement_timeout={config.query_timeout_ms}",
            },
        )

    def discover_schema(self) -> dict[str, list[str]]:
        with self.engine.connect() as conn:
            return {
                c["name"]: [str(c["type"])]
                for c in inspect(conn).get_columns(
                    self.config.table, schema=self.config.schema_name
                )
            }

    def fetch_incremental(self, cursor: dict[str, Any]) -> Iterator[Page]:
        c = self.config
        with self.engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
            with conn.begin():
                conn.execute(text("SET TRANSACTION READ ONLY"))
                table = Table(c.table, MetaData(), schema=c.schema_name, autoload_with=conn)
                columns = [table.c[name] for name in c.fields]
                updated = table.c[c.updated_field]
                identity = {c.key_field, *([c.shop_field] if c.shop_field else [])}
                inspector = inspect(conn)
                unique_keys = [
                    set(
                        inspector.get_pk_constraint(c.table, schema=c.schema_name).get(
                            "constrained_columns"
                        )
                        or []
                    )
                ]
                unique_keys += [
                    set(item["column_names"])
                    for item in inspector.get_unique_constraints(c.table, schema=c.schema_name)
                ]
                if not any(key and key.issubset(identity) for key in unique_keys):
                    raise ConfigurationError("Extraction keys need a primary/unique constraint")
                if any(table.c[name].nullable for name in identity | {c.updated_field}):
                    raise ConfigurationError("Extraction keys and timestamp must be NOT NULL")
                keys = [table.c[c.key_field]]
                if c.shop_field:
                    keys.insert(0, table.c[c.shop_field])
                since = cursor.get("since")
                if not since and cursor.get("watermark"):
                    since = (
                        timestamp(cursor["watermark"]) - timedelta(seconds=c.lookback_seconds)
                    ).isoformat()
                last = cursor.get("last")
                watermark = cursor.get("watermark")
                order_columns = [updated, *keys]
                while True:
                    query = select(*columns)
                    if since:
                        query = query.where(updated >= timestamp(since))
                    if last:
                        values = [timestamp(last[0]), *last[1:]]
                        # Lexicographic keyset pagination with source-native key types.
                        query = query.where(
                            or_(
                                *[
                                    and_(
                                        *(order_columns[j] == values[j] for j in range(i)),
                                        order_columns[i] > values[i],
                                    )
                                    for i in range(len(order_columns))
                                ]
                            )
                        )
                    rows = (
                        conn.execute(query.order_by(*order_columns).limit(c.batch_size))
                        .mappings()
                        .all()
                    )
                    if not rows:
                        yield Page([], {"watermark": watermark})
                        return
                    records = [dict(row) for row in rows]
                    end = records[-1]
                    value = timestamp(end[c.updated_field]).isoformat()
                    if not watermark or timestamp(value) > timestamp(watermark):
                        watermark = value
                    last = [value, *[end[k.name] for k in keys]]
                    yield Page(records, {"since": since, "last": last, "watermark": watermark})

    def close(self) -> None:
        self.engine.dispose()
