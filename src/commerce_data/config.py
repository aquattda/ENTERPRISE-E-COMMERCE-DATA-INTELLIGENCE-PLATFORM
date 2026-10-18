from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CDIP_", env_file=".env", extra="ignore")
    database_url: SecretStr = SecretStr("postgresql+psycopg://localhost/cdip")
    admin_token: SecretStr = SecretStr("")
    reader_token: SecretStr = SecretStr("")
    allowed_http_hosts: str = "mock-api,sheets.googleapis.com,oauth2.googleapis.com"
    allowed_db_hosts: str = "postgres"
    csv_root: Path = Path("tests/fixtures")
    allow_http: bool = False
    request_limit_bytes: int = 1_048_576
    upload_limit_bytes: int = 10_485_760
    secure_cookies: bool = False
    poll_seconds: int = 5
    dispatch_seconds: int = 15
    webhook_max_age_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()
