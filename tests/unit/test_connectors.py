import httpx
import pytest
from pydantic import ValidationError

from commerce_data.connectors.base import ConnectorError, timestamp
from commerce_data.connectors.contracts import CsvConfig, RestConfig, SheetsConfig
from commerce_data.connectors.rest import RestConnector
from commerce_data.connectors.snapshot import CsvConnector, SheetsConnector, rows_to_dicts
from commerce_data.security import ConfigurationError, secret_value


def record(i, updated="2026-01-01T00:00:00Z"):
    return {"id": str(i), "shop_id": "s1", "updated_at": updated, "gross_amount": "100.25"}


def connector(settings, handler, **config):
    return RestConnector(
        RestConfig(base_url="https://mock.test", **config),
        settings,
        httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
    )


def test_pagination_retry_and_resume(settings):
    requests = []
    failed = False

    def handler(request):
        nonlocal failed
        requests.append(dict(request.url.params))
        if request.url.params.get("cursor") == "second":
            if not failed:
                failed = True
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(200, json={"items": [record(2)], "next_cursor": None})
        return httpx.Response(200, json={"items": [record(1)], "next_cursor": "second"})

    conn = connector(settings, handler)
    pages = list(conn.fetch_incremental({}))
    assert [r["id"] for p in pages for r in p.records] == ["1", "2"]
    assert conn.retries == 1 and conn.rate_limits == 1
    assert "page" not in pages[-1].cursor
    resumed = list(conn.fetch_incremental(pages[0].cursor))
    assert resumed[0].records[0]["id"] == "2"
    # Original unbounded scan stays unbounded on resume; pagination cannot shift.
    assert "updated_since" not in requests[-1]


def test_timestamp_lookback_and_monotonic_watermark(settings):
    seen = []

    def handler(request):
        seen.append(request.url.params["updated_since"])
        return httpx.Response(200, json={"items": [record(1, "2025-12-31T23:59:00Z")]})

    pages = list(
        connector(settings, handler).fetch_incremental({"watermark": "2026-01-01T00:00:00+00:00"})
    )
    assert seen == ["2025-12-31T23:55:00+00:00"]
    assert pages[-1].cursor["watermark"] == "2026-01-01T00:00:00+00:00"


@pytest.mark.parametrize("code", [401, 403, 404, 302])
def test_no_retry_on_permanent_errors(settings, code):
    conn = connector(settings, lambda _: httpx.Response(code))
    with pytest.raises(ConnectorError):
        list(conn.fetch_incremental({}))
    assert conn.retries == 0


def test_retry_budget(settings):
    conn = connector(settings, lambda _: httpx.Response(503), max_retries=2)
    with pytest.raises(ConnectorError):
        list(conn.fetch_incremental({}))
    assert conn.retries == 2


def test_cursor_cycle_rejected(settings):
    conn = connector(
        settings, lambda _: httpx.Response(200, json={"items": [], "next_cursor": "x"})
    )
    with pytest.raises(ConnectorError, match="repeated"):
        list(conn.fetch_incremental({}))


def test_retry_after_http_date(settings):
    from datetime import UTC, datetime, timedelta
    from email.utils import format_datetime

    calls = 0
    delays = []

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": format_datetime(datetime.now(UTC) + timedelta(seconds=10))},
            )
        return httpx.Response(200, json={"items": []})

    conn = connector(settings, handler)
    conn.sleep = delays.append
    list(conn.fetch_incremental({}))
    assert any(d >= 8 for d in delays)


def test_host_and_credentials_guard(settings):
    with pytest.raises(ConfigurationError):
        RestConnector(RestConfig(base_url="https://169.254.169.254"), settings)
    with pytest.raises(ValidationError):
        RestConfig(base_url="https://mock.test", secret_ref="plaintext")
    with pytest.raises(ValidationError):
        RestConfig(base_url="https://mock.test", api_key="secret")
    with pytest.raises(ConfigurationError):
        secret_value("env:PATH")


def test_csv_streaming_and_root_guard(settings, tmp_path):
    (tmp_path / "employees.csv").write_text("id;name\nA;One\nB;Two\n", encoding="utf-8")
    conn = CsvConnector(CsvConfig(path="employees.csv", batch_size=1), settings)
    pages = list(conn.fetch_incremental({}))
    assert len(pages) == 2 and pages[1].records == [{"id": "B", "name": "Two"}]
    with pytest.raises(ConfigurationError):
        CsvConnector(CsvConfig(path="../secret.csv"), settings)


def test_csv_invalid_encoding(settings, tmp_path):
    (tmp_path / "bad.csv").write_bytes(b"id,name\n1,\xff")
    with pytest.raises(UnicodeDecodeError):
        list(CsvConnector(CsvConfig(path="bad.csv"), settings).fetch_incremental({}))


def test_missing_headers_and_naive_timestamp():
    with pytest.raises(ConnectorError):
        rows_to_dicts([])
    with pytest.raises(ConnectorError):
        rows_to_dicts([["id", "id"], [1, 2]])
    with pytest.raises(ConnectorError):
        timestamp("2026-01-01T00:00:00")


def test_sheets_batch_get_and_padding(settings, monkeypatch):
    monkeypatch.setenv("CDIP_SECRET_GOOGLE", "not-a-real-token")

    def handler(request):
        assert request.url.path.endswith("/values:batchGet")
        assert request.headers["Authorization"] == "Bearer not-a-real-token"
        return httpx.Response(
            200,
            json={
                "valueRanges": [{"values": [["employee_id", "name"], ["e1", "Synthetic"], ["e2"]]}]
            },
        )

    cfg = SheetsConfig(
        spreadsheet_id="test",
        ranges=["Employees!A1:B10"],
        auth="oauth_token",
        secret_ref="env:CDIP_SECRET_GOOGLE",
        key_field="employee_id",
        batch_size=1,
    )
    conn = SheetsConnector(cfg, settings, httpx.Client(transport=httpx.MockTransport(handler)))
    conn.http.sleep = lambda _: None
    pages = list(conn.fetch_incremental({}))
    assert pages[1].records == [{"employee_id": "e2", "name": None}]
    assert not conn.capabilities.incremental and conn.capabilities.snapshot


def test_oauth_client_credentials(settings, monkeypatch):
    monkeypatch.setenv("CDIP_SECRET_OAUTH", "synthetic-client-secret")
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/token":
            assert b"grant_type=client_credentials" in request.content
            return httpx.Response(200, json={"access_token": "synthetic-access-token"})
        assert request.headers["Authorization"] == "Bearer synthetic-access-token"
        return httpx.Response(200, json={"items": []})

    conn = connector(
        settings,
        handler,
        auth="oauth_client_credentials",
        token_url="https://mock.test/token",
        client_id="test-client",
        client_secret_ref="env:CDIP_SECRET_OAUTH",
    )
    assert len(list(conn.fetch_incremental({}))) == 1
    assert len(requests) == 2


def test_csv_missing_key_header_cannot_infer_deletions(settings, tmp_path):
    (tmp_path / "bad.csv").write_text("wrong_key,name\n", encoding="utf-8")
    with pytest.raises(ConnectorError, match="business key"):
        list(CsvConnector(CsvConfig(path="bad.csv", delimiter=","), settings).fetch_incremental({}))


def test_rest_numeric_decimal_is_lossless(settings):
    from decimal import Decimal

    conn = connector(
        settings,
        lambda _: httpx.Response(
            200,
            content=b'{"items":[{"id":"1","shop_id":"s1","updated_at":"2026-01-01T00:00:00Z",'
            b'"amount":123456789012345678.25}]}',
        ),
    )
    value = list(conn.fetch_incremental({}))[0].records[0]["amount"]
    assert value == Decimal("123456789012345678.25")
    assert isinstance(value, Decimal)


def test_remote_response_byte_budget(settings):
    conn = connector(
        settings, lambda _: httpx.Response(200, content=b"x" * 2048), max_response_bytes=1024
    )
    with pytest.raises(ConnectorError, match="byte budget"):
        list(conn.fetch_incremental({}))
