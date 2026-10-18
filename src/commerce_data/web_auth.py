"""Short-lived signed browser sessions; bearer API clients remain supported."""

import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import HTTPException, Request

from commerce_data.config import Settings

COOKIE = "cdip_session"
LIFETIME = 8 * 60 * 60
_WORKSPACE_KEY = secrets.token_urlsafe(48)


def role_for_token(token: str, settings: Settings) -> str:
    for role, expected in (
        ("admin", settings.admin_token.get_secret_value()),
        ("reader", settings.reader_token.get_secret_value()),
    ):
        if expected and secrets.compare_digest(token, expected):
            return role
    raise HTTPException(401, "Invalid credentials")


def role_key(role: str, settings: Settings) -> str:
    if role == "workspace":
        return settings.admin_token.get_secret_value() or _WORKSPACE_KEY
    if role == "admin":
        return settings.admin_token.get_secret_value()
    if role == "reader":
        return settings.reader_token.get_secret_value()
    return ""


def issue_session(role: str, settings: Settings) -> tuple[str, dict]:
    data = {
        "role": role,
        "expires_at": int(time.time()) + LIFETIME,
        "csrf": secrets.token_urlsafe(32),
    }
    payload = base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
    signature = hmac.new(
        role_key(role, settings).encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return payload + "." + signature, data


def browser_session(request: Request, settings: Settings) -> dict:
    try:
        cookie = request.cookies.get(COOKIE, "")
        if len(cookie) > 1024:
            raise ValueError()
        payload, signature = cookie.split(".")
        data = json.loads(base64.urlsafe_b64decode(payload))
        key = role_key(data["role"], settings)
        expected = hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not key or not secrets.compare_digest(signature, expected):
            raise ValueError()
        if not time.time() < data["expires_at"] <= time.time() + LIFETIME:
            raise ValueError()
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), data["csrf"]):
                raise HTTPException(403, "Invalid browser request")
        return data
    except (ValueError, KeyError, TypeError):
        raise HTTPException(401, "Session expired") from None
