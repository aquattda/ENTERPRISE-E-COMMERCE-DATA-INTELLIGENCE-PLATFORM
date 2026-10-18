"""Read-only source requests. Credentials are transient; no data or secrets are stored."""

import csv
import hashlib
import hmac
import http.client
import io
import ipaddress
import json
import re
import socket
import ssl
import time
from dataclasses import dataclass
from typing import Literal
from urllib.parse import quote, urlencode, urljoin, urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr

MAX_BYTES = 1_000_000


class SourceError(ValueError):
    pass


class SourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["website", "sheets", "shopee", "tiktok"]
    url: str = Field(default="", max_length=6000)
    auth: Literal["none", "bearer", "header"] = "none"
    token: SecretStr = Field(default=SecretStr(""), max_length=8192)
    header_name: str = Field(default="X-API-Key", max_length=80)
    records_path: str = Field(default="", max_length=200)
    sheet_mode: Literal["public", "private"] = "public"
    sheet_range: str = Field(default="A1:Z1000", max_length=200)
    gid: str = Field(default="0", pattern=r"^\d{1,20}$")
    operation: Literal["shops", "orders"] = "shops"
    app_id: str = Field(default="", max_length=160)
    app_secret: SecretStr = Field(default=SecretStr(""), max_length=8192)
    shop_id: str = Field(default="", max_length=300)
    cursor: str = Field(default="", max_length=2000)
    days: int = Field(default=7, ge=1, le=14)
    until: int | None = Field(default=None, ge=1, le=4102444800)


@dataclass
class Outbound:
    url: str
    headers: dict
    method: str = "GET"
    body: bytes | None = None
    records_path: str = ""
    sheets_csv: bool = False
    sheets_values: bool = False


def required(value, label):
    if not value:
        raise SourceError(f"Bạn chưa nhập {label}.")
    return value


def build_request(source: SourceRequest, now: int | None = None) -> Outbound:
    now = now or int(time.time())
    window_end = source.until or now
    if window_end > now:
        raise SourceError("Thời điểm kết thúc không được ở tương lai.")
    token = source.token.get_secret_value()
    secret = source.app_secret.get_secret_value()
    headers = {"Accept": "application/json,text/csv", "Accept-Encoding": "identity"}
    if source.kind == "website":
        required(source.url, "địa chỉ API")
        if source.auth != "none":
            required(token, "token / API key")
            if "\r" in token or "\n" in token:
                raise SourceError("Token không được chứa ký tự xuống dòng.")
            if source.auth == "bearer":
                headers["Authorization"] = "Bearer " + token
            else:
                allowed = {
                    "authorization",
                    "x-api-key",
                    "api-key",
                    "x-auth-token",
                    "token",
                    "x-shopify-access-token",
                }
                if source.header_name.lower() not in allowed:
                    raise SourceError(
                        "Tên header được hỗ trợ: Authorization, "
                        "X-API-Key, API-Key, X-Auth-Token, Token, X-Shopify-Access-Token."
                    )
                headers[source.header_name] = token
        return Outbound(source.url, headers, records_path=source.records_path)
    if source.kind == "sheets":
        url = urlsplit(source.url)
        if (
            url.scheme != "https"
            or url.hostname != "docs.google.com"
            or url.username
            or url.password
        ):
            raise SourceError(
                "Dán liên kết Google Sheets bắt đầu bằng https://docs.google.com/spreadsheets/."
            )
        published = re.fullmatch(r"/spreadsheets/d/e/([A-Za-z0-9_-]+)/pub/?", url.path)
        match = re.match(r"^/spreadsheets/d/([A-Za-z0-9_-]+)(?:/|$)", url.path)
        if published and source.sheet_mode == "public":
            return Outbound(
                f"https://docs.google.com/spreadsheets/d/e/{published[1]}/pub?"
                + urlencode({"output": "csv", "gid": source.gid}),
                headers,
                sheets_csv=True,
            )
        if not match or match[1] == "e":
            raise SourceError(
                "Liên kết bảng tính chưa đúng. Dùng liên kết mở bảng "
                "tính hoặc liên kết xuất CSV đã công bố."
            )
        sheet_id = match[1]
        if source.sheet_mode == "private":
            required(token, "Google Access token có quyền đọc bảng tính")
            headers["Authorization"] = "Bearer " + token
            return Outbound(
                f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/"
                + quote(source.sheet_range, safe=""),
                headers,
                sheets_values=True,
            )
        return Outbound(
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?"
            + urlencode({"tqx": "out:csv", "gid": source.gid}),
            headers,
            sheets_csv=True,
        )
    required(source.app_id, "Partner ID / App key")
    required(secret, "Partner key / App secret")
    required(token, "Access token được cấp quyền")
    if source.kind == "shopee":
        if not source.app_id.isdigit() or not source.shop_id.isdigit():
            raise SourceError("Partner ID và Shop ID của Shopee phải là số.")
        path = (
            "/api/v2/shop/get_shop_info"
            if source.operation == "shops"
            else "/api/v2/order/get_order_list"
        )
        base = f"{source.app_id}{path}{now}{token}{source.shop_id}"
        params = {
            "partner_id": source.app_id,
            "timestamp": str(now),
            "access_token": token,
            "shop_id": source.shop_id,
            "sign": hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest(),
        }
        if source.operation == "orders":
            params.update(
                time_range_field="create_time",
                time_from=str(window_end - source.days * 86400),
                time_to=str(window_end),
                page_size="20",
            )
            if source.cursor:
                params["cursor"] = source.cursor
        return Outbound(
            "https://partner.shopeemobile.com" + path + "?" + urlencode(params),
            headers,
            records_path="response.order_list" if source.operation == "orders" else "response",
        )
    path = (
        "/authorization/202309/shops"
        if source.operation == "shops"
        else "/order/202309/orders/search"
    )
    params = {"app_key": source.app_id, "timestamp": str(now)}
    body = None
    if source.operation == "orders":
        required(source.shop_id, "Shop cipher (lấy từ danh sách cửa hàng)")
        params.update(shop_cipher=source.shop_id, page_size="20")
        if source.cursor:
            params["page_token"] = source.cursor
        body = json.dumps(
            {"create_time_ge": window_end - source.days * 86400, "create_time_lt": window_end},
            separators=(",", ":"),
        ).encode()
    signed = path + "".join(k + params[k] for k in sorted(params)) + (body.decode() if body else "")
    params["sign"] = hmac.new(
        secret.encode(), (secret + signed + secret).encode(), hashlib.sha256
    ).hexdigest()
    headers["x-tts-access-token"] = token
    headers["Content-Type"] = "application/json"
    return Outbound(
        "https://open-api.tiktokglobalshop.com" + path + "?" + urlencode(params),
        headers,
        "POST" if body else "GET",
        body,
        "data.orders" if source.operation == "orders" else "data.shops",
    )


def public_target(url):
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError
        if any(ord(c) < 33 or ord(c) > 126 for c in url):
            raise ValueError
        host = parsed.hostname
        addresses = list(
            dict.fromkeys(
                str(r[4][0]) for r in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            )
        )
        if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
            raise ValueError
        # Prefer IPv4 where available; every returned address was validated before connecting.
        addresses.sort(key=lambda ip: ":" in ip)
        return parsed, addresses[0]
    except (ValueError, OSError):
        raise SourceError(
            "Chỉ hỗ trợ API HTTPS trên Internet, cổng 443. Địa chỉ nội "
            "bộ hoặc tên miền không hợp lệ không được hỗ trợ."
        ) from None


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address):
        self.tls_context = ssl.create_default_context()
        super().__init__(host, timeout=12, context=self.tls_context)
        self.address = address

    def connect(self):
        # Pin the validated IP: no second DNS lookup (prevents DNS rebinding).
        sock = socket.create_connection((self.address, 443), timeout=self.timeout)
        try:
            self.sock = self.tls_context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def fetch(outbound: Outbound):
    url = outbound.url
    for _ in range(4):
        parsed, address = public_target(url)
        connection = PinnedHTTPS(parsed.hostname, address)
        try:
            path = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
            connection.request(outbound.method, path, body=outbound.body, headers=outbound.headers)
            response = connection.getresponse()
            if 300 <= response.status < 400:
                destination = urljoin(url, response.getheader("Location", ""))
                host = urlsplit(destination).hostname or ""
                if outbound.sheets_csv and (
                    host == "docs.google.com" or host.endswith(".googleusercontent.com")
                ):
                    url = destination
                    continue
                raise SourceError(
                    "Nguồn chuyển hướng sang địa chỉ khác. Dùng URL "
                    "API cuối cùng; với Sheets, kiểm tra quyền truy cập."
                )
            if response.status in (401, 403):
                raise SourceError(
                    "Nguồn từ chối quyền truy cập (401/403). Kiểm tra "
                    "token, quyền ứng dụng và quyền chia sẻ dữ liệu."
                )
            if response.status == 429:
                raise SourceError("Nguồn đang giới hạn số yêu cầu (429). Chờ một lúc rồi thử lại.")
            if response.status >= 400:
                raise SourceError(
                    f"Nguồn trả HTTP {response.status}. Kiểm tra đường dẫn và thông tin yêu cầu."
                )
            if response.getheader("Content-Encoding", "identity") not in ("", "identity"):
                raise SourceError(
                    "Nguồn trả dữ liệu nén không được hỗ trợ. Yêu cầu phản hồi không nén."
                )
            payload = bytearray()
            started = time.monotonic()
            while True:
                if time.monotonic() - started > 20:
                    raise SourceError("Nguồn trả dữ liệu quá chậm. Thu hẹp phạm vi rồi thử lại.")
                chunk = response.read(min(65536, MAX_BYTES + 1 - len(payload)))
                if not chunk:
                    break
                payload.extend(chunk)
                if len(payload) > MAX_BYTES:
                    raise SourceError(
                        "Phản hồi vượt 1 MB. Dùng phân trang hoặc thu hẹp phạm vi dữ liệu."
                    )
            return bytes(payload), response.getheader("Content-Type", ""), response.status
        except SourceError:
            raise
        except (OSError, http.client.HTTPException, ValueError):
            raise SourceError(
                "Không kết nối được tới nguồn. Kiểm tra URL, chứng chỉ "
                "HTTPS và khả năng truy cập từ Internet."
            ) from None
        finally:
            connection.close()
    raise SourceError("Nguồn chuyển hướng quá nhiều lần.")


def at_path(value, path):
    if not path:
        return value
    try:
        for key in path.split("."):
            value = value[int(key)] if isinstance(value, list) else value[key]
        return value
    except (KeyError, IndexError, TypeError, ValueError):
        raise SourceError(
            "Không tìm thấy đường dẫn danh sách trong JSON. Xóa ô "
            "đường dẫn để xem phản hồi gốc rồi nhập lại, ví dụ data.items."
        ) from None


def table_values(values):
    if not values:
        return []
    if not all(isinstance(row, list) for row in values):
        raise SourceError("Dữ liệu bảng tính không đúng định dạng hàng/cột.")
    width = max(len(row) for row in values)
    if width > 200:
        raise SourceError("Bảng có hơn 200 cột. Thu hẹp vùng dữ liệu.")
    names = []
    for i in range(width):
        name = str(values[0][i]) if i < len(values[0]) and str(values[0][i]) else f"Cột {i + 1}"
        original = name
        suffix = 2
        while name in names:
            name = f"{original} ({suffix})"
            suffix += 1
        names.append(name)
    return [dict(zip(names, row + [""] * (width - len(row)), strict=True)) for row in values[1:]]


def mask(value, secrets, depth=0):
    if depth > 60:
        raise SourceError("JSON lồng nhau quá sâu để hiển thị.")
    if isinstance(value, dict):
        return {
            k: "[đã ẩn]"
            if re.search(
                r"^(access_token|refresh_token|app_secret|partner_key|authorization|api_key)$",
                k,
                re.I,
            )
            else mask(v, secrets, depth + 1)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [mask(v, secrets, depth + 1) for v in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[đã ẩn]")
    return value


def read_source(source: SourceRequest):
    started = time.monotonic()
    if (
        source.kind in ("shopee", "tiktok")
        and source.operation == "orders"
        and source.until is None
    ):
        source = source.model_copy(update={"until": int(time.time())})
    outbound = build_request(source)
    payload, content_type, status = fetch(outbound)
    try:
        text = payload.decode("utf-8-sig")
        if "text/html" in content_type or text.lstrip().lower().startswith(
            ("<!doctype html", "<html")
        ):
            raise SourceError(
                "Địa chỉ trả về trang web HTML, không phải API "
                "JSON/CSV. Với Google Sheets, kiểm tra quyền đọc hoặc dùng Access token."
            )
        is_csv = outbound.sheets_csv or "csv" in content_type
        if is_csv:
            raw = table_values(list(csv.reader(io.StringIO(text))))
        else:
            raw = json.loads(
                text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value))
            )
    except (UnicodeError, ValueError, csv.Error, RecursionError) as error:
        if isinstance(error, SourceError):
            raise
        raise SourceError("Nguồn không trả JSON hoặc CSV UTF-8 hợp lệ.") from None
    if (source.kind in ("shopee", "tiktok") or outbound.sheets_values) and not isinstance(
        raw, dict
    ):
        raise SourceError("Nguồn trả dữ liệu không đúng cấu trúc API được chọn.")
    if isinstance(raw, dict):
        failed = (source.kind == "shopee" and bool(raw.get("error"))) or (
            source.kind == "tiktok" and raw.get("code") not in (0, "0", None)
        )
        if failed:
            raise SourceError(
                "Sàn trả lỗi nghiệp vụ. Kiểm tra quyền API, thời hạn "
                "token, Shop ID/cipher và môi trường production. Chưa lấy được dữ liệu."
            )
    cursor = ""
    if source.kind == "shopee" and source.operation == "orders":
        section = raw.get("response", {})
        if not isinstance(section, dict):
            raise SourceError("Shopee không trả cấu trúc dữ liệu đơn hàng hợp lệ.")
        if section.get("more"):
            cursor = str(section.get("next_cursor", ""))
    if source.kind == "tiktok" and source.operation == "orders":
        section = raw.get("data") or {}
        if not isinstance(section, dict):
            raise SourceError("TikTok Shop không trả cấu trúc dữ liệu đơn hàng hợp lệ.")
        cursor = str(section.get("next_page_token") or "")
    if outbound.sheets_values:
        records = table_values(raw.get("values", []))
    else:
        records = at_path(raw, source.records_path or outbound.records_path)
        if isinstance(records, dict):
            # Auto-detect only common list containers; raw remains available for other shapes.
            found = next(
                (
                    records[k]
                    for k in ("items", "data", "results", "rows")
                    if isinstance(records.get(k), list)
                ),
                None,
            )
            records = found if found is not None else [records]
        if not isinstance(records, list):
            records = [{"value": records}]
        records = [v if isinstance(v, dict) else {"value": v} for v in records]
    if len(records) > 5000:
        raise SourceError(
            "Có hơn 5.000 dòng trong một phản hồi. Thu hẹp phạm vi hoặc dùng phân trang."
        )
    secrets = [source.token.get_secret_value(), source.app_secret.get_secret_value()]
    return {
        "rows": mask(records, secrets),
        "raw": mask(raw, secrets),
        "row_count": len(records),
        "http_status": status,
        "elapsed_ms": round((time.monotonic() - started) * 1000),
        "bytes": len(payload),
        "next_cursor": cursor,
        "kind": source.kind,
        "window_end": source.until,
        "scope": "Một phản hồi / một trang từ nguồn; chưa phải toàn bộ dữ liệu.",
    }
