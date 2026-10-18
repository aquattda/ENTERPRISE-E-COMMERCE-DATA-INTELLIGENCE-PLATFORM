"""Create local-only random credentials without printing them or overwriting existing files."""

import secrets
from pathlib import Path

path = Path(".env")
if path.exists():
    raise SystemExit(".env already exists; kept unchanged")
keys = [
    "POSTGRES_PASSWORD",
    "CDIP_MIGRATOR_PASSWORD",
    "CDIP_APP_PASSWORD",
    "CDIP_BI_PASSWORD",
    "PREFECT_DB_PASSWORD",
    "METABASE_DB_PASSWORD",
    "METABASE_ENCRYPTION_SECRET_KEY",
    "CDIP_ADMIN_TOKEN",
    "CDIP_READER_TOKEN",
    "CDIP_SECRET_DEMO_WEBHOOK",
]
values = {key: secrets.token_hex(24) for key in keys}
values["PREFECT_AUTH_STRING"] = "admin:" + secrets.token_hex(24)
with path.open("x", encoding="utf-8") as handle:
    handle.write("".join(f"{key}={value}\n" for key, value in values.items()))
try:
    path.chmod(0o600)
except OSError:
    pass
print("Created .env with random local credentials; values not displayed.")
