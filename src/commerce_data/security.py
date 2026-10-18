import os
import re
from urllib.parse import urlsplit


class ConfigurationError(ValueError):
    pass


def secret_value(reference: str | None) -> str:
    """Only resolve explicitly namespaced env references; never serialize their values."""
    if not reference or not re.fullmatch(r"env:CDIP_SECRET_[A-Z0-9_]+", reference):
        raise ConfigurationError("Expected env:CDIP_SECRET_NAME reference")
    value = os.environ.get(reference[4:])
    if not value:
        raise ConfigurationError("Required secret is not configured")
    return value


def validate_url(url: str, allowed_hosts: str, allow_http: bool = False) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme not in ({"http", "https"} if allow_http else {"https"})
        or parsed.hostname not in allowed_hosts.split(",")
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ConfigurationError(
            "URL must use an allowed host and scheme, without credentials/query"
        )
