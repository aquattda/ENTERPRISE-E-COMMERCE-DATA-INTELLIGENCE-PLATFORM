import csv
import json
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import httpx

from commerce_data.config import Settings
from commerce_data.connectors.base import Capabilities, Connector, ConnectorError, Page
from commerce_data.connectors.contracts import CsvConfig, RestConfig, SheetsConfig
from commerce_data.connectors.rest import RestConnector
from commerce_data.security import ConfigurationError, secret_value


def rows_to_dicts(values: list[list[Any]]) -> list[dict[str, Any]]:
    if not values:
        raise ConnectorError("Snapshot is missing its header; refusing deletion inference")
    headers = values[0]
    if any(not isinstance(h, str) or not h.strip() for h in headers):
        raise ConnectorError("Headers must be non-empty strings")
    if len(set(headers)) != len(headers):
        raise ConnectorError("Duplicate headers")
    result = []
    for row in values[1:]:
        if not any(v not in (None, "") for v in row):
            continue
        if len(row) > len(headers):
            raise ConnectorError("Row exceeds header width")
        result.append(dict(zip(headers, row + [None] * (len(headers) - len(row)), strict=True)))
    return result


class CsvConnector(Connector):
    capabilities = Capabilities(snapshot=True)

    def __init__(self, config: CsvConfig, settings: Settings):
        self.config = config
        root = settings.csv_root.resolve()
        self.path = (root / config.path).resolve()
        if not self.path.is_relative_to(root) or self.path.suffix.lower() != ".csv":
            raise ConfigurationError("CSV path must remain under the configured import directory")

    def fetch_incremental(self, cursor: dict[str, Any]) -> Iterator[Page]:
        with self.path.open(encoding=self.config.encoding, errors="strict", newline="") as handle:
            sample = handle.read(8192)
            handle.seek(0)
            delimiter = (
                self.config.delimiter or csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
            )
            reader = csv.reader(handle, delimiter=delimiter)
            headers = next(reader, [])
            rows_to_dicts([headers])
            if self.config.key_field not in headers:
                raise ConnectorError("Snapshot header is missing its business key")
            if not headers:
                raise ConnectorError("CSV is missing headers")
            batch = []
            for row in reader:
                batch.extend(rows_to_dicts([headers, row]))
                if len(batch) >= self.config.batch_size:
                    yield Page(batch)
                    batch = []
            if batch:
                yield Page(batch)


class SheetsConnector(Connector):
    capabilities = Capabilities(snapshot=True)

    def __init__(
        self, config: SheetsConfig, settings: Settings, client: httpx.Client | None = None
    ):
        self.config = config
        self.http = RestConnector(
            RestConfig(base_url="https://sheets.googleapis.com", requests_per_second=1),
            settings,
            client,
        )
        self.headers: dict[str, str] = {}

    def authenticate(self) -> None:
        value = secret_value(self.config.secret_ref)
        if self.config.auth == "service_account":
            from google.auth.transport.requests import Request
            from google.oauth2.service_account import Credentials

            info = json.loads(value)
            # Do not allow credential documents to redirect a signed assertion to arbitrary hosts.
            if info.get("token_uri") != "https://oauth2.googleapis.com/token":
                raise ConfigurationError("Unexpected Google token URI")
            credentials = Credentials.from_service_account_info(
                info, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
            )
            credentials.refresh(Request())
            value = credentials.token
        self.headers = {"Authorization": f"Bearer {value}"}

    def get_metadata(self) -> dict[str, Any]:
        self.authenticate()
        response = self.http.request(
            "GET",
            self._url(),
            headers=self.headers,
            params={"fields": "spreadsheetId,properties.title,sheets.properties"},
        )
        return {**super().get_metadata(), "spreadsheet": response.json()}

    def _url(self) -> str:
        return f"https://sheets.googleapis.com/v4/spreadsheets/{self.config.spreadsheet_id}"

    def fetch_incremental(self, cursor: dict[str, Any]) -> Iterator[Page]:
        self.authenticate()
        count = 0
        expected_headers = None
        # Every configured range includes headers; large sheets need bounded explicit ranges.
        for offset in range(0, len(self.config.ranges), 10):
            params = [("ranges", r) for r in self.config.ranges[offset : offset + 10]]
            params += [("majorDimension", "ROWS"), ("valueRenderOption", "UNFORMATTED_VALUE")]
            response = self.http.request(
                "GET", self._url() + "/values:batchGet", headers=self.headers, params=params
            )
            ranges = response.json(parse_float=Decimal).get("valueRanges", [])
            if len(ranges) != len(self.config.ranges[offset : offset + 10]):
                raise ConnectorError("Incomplete Sheets response")
            for value_range in ranges:
                values = value_range.get("values", [])
                if not values or self.config.key_field not in values[0]:
                    raise ConnectorError("Snapshot header is missing its business key")
                if expected_headers is not None and values[0] != expected_headers:
                    raise ConnectorError("Snapshot range headers do not match")
                expected_headers = values[0]
                rows = rows_to_dicts(values)
                count += len(rows)
                if count > self.config.max_snapshot_rows:
                    raise ConnectorError("Snapshot row budget exceeded")
                for start in range(0, len(rows), self.config.batch_size):
                    yield Page(rows[start : start + self.config.batch_size])

    @property
    def retries(self) -> int:  # type: ignore[override]
        return self.http.retries

    @property
    def rate_limits(self) -> int:  # type: ignore[override]
        return self.http.rate_limits

    def close(self) -> None:
        self.http.close()
