from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class ConnectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class Capabilities:
    incremental: bool = False
    snapshot: bool = False
    fetch_by_ids: bool = False
    field_selection: bool = False
    webhooks: bool = False


@dataclass
class Page:
    records: list[dict[str, Any]]
    cursor: dict[str, Any] = field(default_factory=dict)


def timestamp(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ConnectorError("Source timestamps must include a timezone")
    return parsed.astimezone(UTC)


class Connector(ABC):
    capabilities = Capabilities()
    retries = 0
    rate_limits = 0

    def authenticate(self) -> None:
        return None

    @abstractmethod
    def fetch_incremental(self, cursor: dict[str, Any]) -> Iterator[Page]: ...

    def fetch_sample(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("Sample limit must be between 1 and 1000")
        output: list[dict[str, Any]] = []
        pages = self.fetch_incremental({})
        try:
            for page in pages:
                output.extend(page.records[: limit - len(output)])
                if len(output) >= limit:
                    break
        finally:
            pages.close()  # type: ignore[attr-defined]
        return output

    def discover_schema(self) -> dict[str, list[str]]:
        schema: dict[str, set[str]] = {}
        for record in self.fetch_sample():
            for key, value in record.items():
                schema.setdefault(key, set()).add(type(value).__name__)
        return {key: sorted(types) for key, types in schema.items()}

    def get_metadata(self) -> dict[str, Any]:
        return {
            "capabilities": self.capabilities.__dict__,
            "statistics_scope": "sample",
            "estimated_record_count": None,
        }

    def validate_connection(self) -> bool:
        self.authenticate()
        self.fetch_sample(1)
        return True

    def healthcheck(self) -> bool:
        return self.validate_connection()

    def fetch_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        raise NotImplementedError("This connector does not support fetch_by_ids")

    def close(self) -> None:
        return None
