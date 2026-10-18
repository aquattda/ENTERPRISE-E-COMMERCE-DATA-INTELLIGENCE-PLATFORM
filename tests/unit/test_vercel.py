import hashlib
import hmac
import json
import socket
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from apps.vercel import sources
from apps.vercel.main import app
from apps.vercel.sources import (
    SourceError,
    SourceRequest,
    build_request,
    public_target,
    read_source,
)

client = TestClient(app)
HEADERS = {"X-CDIP-Request": "1"}


def test_home_is_connections_not_analytics():
    response = client.get("/")
    assert response.status_code == 200
    assert "connections.js" in response.text
    assert "Lãi/lỗ" not in response.text
    assert client.get("/api/v1/business/report").status_code == 404
    assert client.get("/api/v1/health").json()["service"] == "source-connections"


def test_example_is_explicit_and_no_storage():
    result = client.get("/api/sources/example")
    assert result.json()["example"] is True
    assert len(result.json()["items"]) == 3
    assert result.headers["Cache-Control"] == "no-store"


def test_validation_and_origin_never_echo_secrets():
    secret = "do-not-return-this-value"
    r = client.post("/api/sources/read", headers=HEADERS, json={"kind": secret, "token": secret})
    assert r.status_code == 422 and secret not in r.text
    assert client.post("/api/sources/read", json={}).status_code == 403
    assert (
        client.post(
            "/api/sources/read", headers={**HEADERS, "Origin": "https://untrusted.example"}, json={}
        ).status_code
        == 403
    )
    assert client.post("/api/sources/read", headers=HEADERS, content="x" * 32001).status_code == 413


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://127.0.0.1",
        "https://10.0.0.1",
        "https://[::1]",
        "https://example.com:8080",
        "https://u:p@example.com",
        "https://example.com/#x",
    ],
)
def test_reject_unsafe_targets(monkeypatch, url):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("127.0.0.1", 443))])
    with pytest.raises(SourceError):
        public_target(url)


def test_dns_all_answers_public_and_ip_pinned(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("8.8.8.8", 443)), (2, 1, 6, "", ("10.0.0.1", 443))],
    )
    with pytest.raises(SourceError):
        public_target("https://example.com")
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("8.8.8.8", 443))])
    parsed, address = public_target("https://example.com/data")
    conn = sources.PinnedHTTPS(parsed.hostname, address)
    assert conn.address == "8.8.8.8" and conn.host == "example.com"


def test_website_bearer_and_header_restrictions():
    request = build_request(
        SourceRequest(kind="website", url="https://example.com/api", auth="bearer", token="secret")
    )
    assert request.headers["Authorization"] == "Bearer secret"
    with pytest.raises(SourceError):
        build_request(
            SourceRequest(
                kind="website",
                url="https://example.com",
                auth="header",
                token="x",
                header_name="Host",
            )
        )


def test_shopee_signature_and_paging_window():
    body = SourceRequest(
        kind="shopee",
        app_id="123",
        app_secret="key",
        token="token",
        shop_id="456",
        operation="orders",
        until=1700000000,
        cursor="next",
    )
    out = build_request(body, 1700000030)
    q = parse_qs(urlsplit(out.url).query)
    signed = b"123/api/v2/order/get_order_list1700000030token456"
    assert q["sign"] == [hmac.new(b"key", signed, hashlib.sha256).hexdigest()]
    assert q["time_to"] == ["1700000000"] and q["cursor"] == ["next"]
    assert out.method == "GET" and "key" not in out.url


def test_tiktok_signs_exact_body_and_token_only_in_header():
    source = SourceRequest(
        kind="tiktok",
        app_id="abc",
        app_secret="key",
        token="private-token",
        shop_id="cipher",
        operation="orders",
        until=1700000000,
    )
    out = build_request(source, 1700000030)
    q = parse_qs(urlsplit(out.url).query)
    signed = (
        b"key/order/202309/orders/searchapp_keyabcpage_size20shop_cipherciphertimestamp1700000030"
        + out.body
        + b"key"
    )
    assert q["sign"] == [hmac.new(b"key", signed, hashlib.sha256).hexdigest()]
    assert "private-token" not in out.url
    assert out.headers["x-tts-access-token"] == "private-token"
    assert out.method == "POST" and json.loads(out.body)["create_time_lt"] == 1700000000


def test_google_build_public_private_and_bad_url():
    public = build_request(
        SourceRequest(kind="sheets", url="https://docs.google.com/spreadsheets/d/abc/edit#gid=0")
    )
    assert public.sheets_csv and "tqx=out%3Acsv" in public.url
    private = build_request(
        SourceRequest(
            kind="sheets",
            url="https://docs.google.com/spreadsheets/d/abc/edit",
            sheet_mode="private",
            token="private",
        )
    )
    assert private.sheets_values and private.url.startswith("https://sheets.googleapis.com/")
    assert private.headers["Authorization"] == "Bearer private"
    with pytest.raises(SourceError):
        build_request(
            SourceRequest(kind="sheets", url="https://docs.google.com.evil.test/spreadsheets/d/abc")
        )


def test_table_json_secrets_mask_and_csv_preserves_duplicate_columns(monkeypatch):
    monkeypatch.setattr(
        sources,
        "fetch",
        lambda out: (
            b'{"data":{"items":[{"name":"ok","access_token":"abc","echo":"my-secret"}]} }',
            "application/json",
            200,
        ),
    )
    result = read_source(
        SourceRequest(
            kind="website",
            url="https://example.com",
            auth="bearer",
            token="my-secret",
            records_path="data.items",
        )
    )
    assert result["row_count"] == 1
    assert "my-secret" not in json.dumps(result)
    assert result["rows"][0]["access_token"] == "[đã ẩn]"
    monkeypatch.setattr(sources, "fetch", lambda out: (b"name,name,\nA,B,C\n", "text/csv", 200))
    result = read_source(SourceRequest(kind="website", url="https://example.com"))
    assert list(result["rows"][0].values()) == ["A", "B", "C"]
    assert len(result["rows"][0]) == 3


def test_private_google_values_and_empty_result(monkeypatch):
    monkeypatch.setattr(
        sources,
        "fetch",
        lambda out: (b'{"values":[["sku","qty"],["A",2],["B"]]}', "application/json", 200),
    )
    result = read_source(
        SourceRequest(
            kind="sheets",
            url="https://docs.google.com/spreadsheets/d/abc/edit",
            sheet_mode="private",
            token="oauth",
        )
    )
    assert result["rows"] == [{"sku": "A", "qty": 2}, {"sku": "B", "qty": ""}]
    monkeypatch.setattr(sources, "fetch", lambda out: (b"[]", "application/json", 200))
    assert read_source(SourceRequest(kind="website", url="https://example.com"))["rows"] == []


@pytest.mark.parametrize(
    "payload,ctype",
    [
        (b"<html>Login</html>", "text/html"),
        (b"{broken", "application/json"),
        (b"NaN", "application/json"),
    ],
)
def test_bad_response_is_not_success(monkeypatch, payload, ctype):
    monkeypatch.setattr(sources, "fetch", lambda out: (payload, ctype, 200))
    r = client.post(
        "/api/sources/read", headers=HEADERS, json={"kind": "website", "url": "https://example.com"}
    )
    assert r.status_code == 400 and "error" in r.json()


def test_marketplace_business_error_and_next_page(monkeypatch):
    source = SourceRequest(
        kind="shopee", app_id="1", app_secret="key", token="access", shop_id="2", operation="orders"
    )
    monkeypatch.setattr(
        sources,
        "fetch",
        lambda out: (b'{"error":"invalid_token","message":"private"}', "application/json", 200),
    )
    with pytest.raises(SourceError):
        read_source(source)
    monkeypatch.setattr(
        sources,
        "fetch",
        lambda out: (
            b'{"error":"","response":{"order_list":[{"order_sn":"A"}],"more":true,"next_cursor":"page2"}}',
            "application/json",
            200,
        ),
    )
    result = read_source(source)
    assert result["next_cursor"] == "page2" and result["rows"] == [{"order_sn": "A"}]
    assert result["window_end"] > 0


@pytest.mark.parametrize("case", ["redirect", "too_large", "unauthorized"])
def test_fetch_rejects_redirects_size_and_auth_errors(monkeypatch, case):
    class FakeResponse:
        status = {"redirect": 302, "too_large": 200, "unauthorized": 401}[case]

        def getheader(self, name, default=""):
            return {
                "Location": "https://127.0.0.1/private",
                "Content-Type": "application/json",
            }.get(name, default)

        def read(self, size):
            return b"x" * size

    class FakeConnection:
        def __init__(self, *a):
            pass

        def request(self, *a, **kw):
            pass

        def getresponse(self):
            return FakeResponse()

        def close(self):
            pass

    monkeypatch.setattr(sources, "public_target", lambda url: (urlsplit(url), "8.8.8.8"))
    monkeypatch.setattr(sources, "PinnedHTTPS", FakeConnection)
    with pytest.raises(SourceError):
        sources.fetch(sources.Outbound("https://example.com", {}))


def test_pin_connects_validated_address_with_original_tls_hostname(monkeypatch):
    events = []
    fake_socket = object()

    class Context:
        def wrap_socket(self, sock, server_hostname):
            events.append(("tls", server_hostname))
            return sock

    monkeypatch.setattr(
        sources.socket,
        "create_connection",
        lambda address, timeout: events.append(("ip", address)) or fake_socket,
    )
    conn = sources.PinnedHTTPS("example.com", "8.8.8.8")
    conn.tls_context = Context()
    conn.connect()
    assert events == [("ip", ("8.8.8.8", 443)), ("tls", "example.com")]
