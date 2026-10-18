import random
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from commerce_data.config import Settings
from commerce_data.connectors.base import Capabilities, Connector, ConnectorError, Page, timestamp
from commerce_data.connectors.contracts import RestConfig
from commerce_data.security import secret_value, validate_url


class RestConnector(Connector):
    capabilities = Capabilities(incremental=True, webhooks=True)

    def __init__(
        self,
        config: RestConfig,
        settings: Settings,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.config = config
        self.settings = settings
        validate_url(config.base_url, settings.allowed_http_hosts, settings.allow_http)
        self.client = client or httpx.Client(timeout=config.timeout_seconds, follow_redirects=False)
        self.sleep = sleep
        self.headers: dict[str, str] = {}
        self.last_request = 0.0
        self.retries = 0
        self.rate_limits = 0
        self.capabilities = Capabilities(
            incremental=True, webhooks=True, field_selection=bool(config.fields_param)
        )

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(self.config.max_retries + 1):
            self.sleep(
                max(0, 1 / self.config.requests_per_second - (time.monotonic() - self.last_request))
            )
            self.last_request = time.monotonic()
            response = None
            try:
                with self.client.stream(method, url, **kwargs) as response:
                    if 200 <= response.status_code < 300:
                        content = bytearray()
                        for chunk in response.iter_bytes():
                            if len(content) + len(chunk) > self.config.max_response_bytes:
                                raise ConnectorError("Remote response byte budget exceeded")
                            content.extend(chunk)
                        # iter_bytes has already decoded transport compression.
                        headers = {
                            k: v
                            for k, v in response.headers.items()
                            if k.lower() not in {"content-encoding", "content-length"}
                        }
                        return httpx.Response(
                            response.status_code,
                            headers=headers,
                            content=bytes(content),
                            request=response.request,
                        )
                    if response.status_code == 429:
                        self.rate_limits += 1
                    elif response.status_code < 500:
                        raise ConnectorError(f"Remote HTTP status {response.status_code}")
            except httpx.TransportError:
                pass
            if attempt == self.config.max_retries:
                raise ConnectorError("Remote request retry budget exhausted")
            delay = min(30, 2**attempt) + random.uniform(0, 1)
            if response is not None and response.headers.get("Retry-After"):
                retry_after = response.headers["Retry-After"]
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    try:
                        delay = max(
                            delay,
                            (
                                parsedate_to_datetime(retry_after) - datetime.now(UTC)
                            ).total_seconds(),
                        )
                    except (ValueError, TypeError):
                        pass
                if delay > 300:
                    raise ConnectorError("Retry-After exceeds job wait budget; retry later")
            self.retries += 1
            self.sleep(delay)
        raise ConnectorError("Unreachable retry state")

    def authenticate(self) -> None:
        c = self.config
        if c.auth == "bearer":
            self.headers = {"Authorization": f"Bearer {secret_value(c.secret_ref)}"}
        elif c.auth == "oauth_client_credentials":
            assert c.token_url
            validate_url(c.token_url, self.settings.allowed_http_hosts, self.settings.allow_http)
            data = self.request(
                "POST",
                c.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": c.client_id,
                    "client_secret": secret_value(c.client_secret_ref),
                },
            ).json()
            self.headers = {"Authorization": f"Bearer {data['access_token']}"}

    def fetch_incremental(self, cursor: dict[str, Any]) -> Iterator[Page]:
        self.authenticate()
        c = self.config
        watermark = cursor.get("watermark")
        since = cursor.get("since")
        if "page" not in cursor and watermark:
            since = (timestamp(watermark) - timedelta(seconds=c.lookback_seconds)).isoformat()
        page_token = cursor.get("page")
        seen: set[str] = set()
        for _ in range(c.max_pages):
            params: dict[str, Any] = {c.limit_param: c.batch_size}
            if since:
                params[c.since_param] = since
            if page_token is not None:
                params[c.cursor_param] = page_token
            if c.fields_param and c.fields:
                params[c.fields_param] = ",".join(c.fields)
            response = self.request(
                "GET", c.base_url.rstrip("/") + c.path, params=params, headers=self.headers
            )
            body = response.json(parse_float=Decimal)
            records = body.get(c.items_field)
            if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
                raise ConnectorError("Response items must be an array of objects")
            if len(records) > c.batch_size:
                raise ConnectorError("Remote page exceeded configured batch size")
            for record in records:
                if c.updated_field and record.get(c.updated_field):
                    value = timestamp(record[c.updated_field]).isoformat()
                    if not watermark or timestamp(value) > timestamp(watermark):
                        watermark = value
            next_token = body.get(c.next_cursor_field)
            if next_token is not None and not isinstance(next_token, (str, int)):
                raise ConnectorError("Invalid pagination cursor")
            final = next_token is None or next_token == ""
            if not final:
                token = str(next_token)
                if token in seen or token == str(page_token):
                    raise ConnectorError("Pagination cursor repeated")
                seen.add(token)
            state = {"watermark": watermark}
            if not final:
                state.update(page=next_token, since=since)
            yield Page(records, state)
            if final:
                return
            page_token = next_token
        raise ConnectorError("Pagination limit reached; checkpoint retained for resume")

    def close(self) -> None:
        self.client.close()
