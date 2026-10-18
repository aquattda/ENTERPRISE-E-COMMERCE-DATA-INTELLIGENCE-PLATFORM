import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator


class CommonConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity: str = Field(default="orders", min_length=1, max_length=80)
    key_field: str = "id"
    shop_field: str | None = "shop_id"
    shop_key: str = Field(default="default", max_length=160)
    updated_field: str | None = "updated_at"
    deleted_field: str = "deleted"
    batch_size: int = Field(default=500, ge=1, le=5000)
    field_mapping: dict[str, str] = Field(default_factory=dict)
    webhook_secret_ref: str | None = None
    reconciliation_interval_seconds: int = Field(default=86400, ge=300, le=2592000)

    @field_validator("webhook_secret_ref", "secret_ref", "client_secret_ref", check_fields=False)
    @classmethod
    def secret_reference(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"env:CDIP_SECRET_[A-Z0-9_]+", value):
            raise ValueError("Only env:CDIP_SECRET_NAME references are accepted")
        return value


class RestConfig(CommonConfig):
    kind: Literal["rest"] = "rest"
    base_url: str
    path: str = "/orders"
    auth: Literal["none", "bearer", "oauth_client_credentials"] = "none"
    secret_ref: str | None = None
    token_url: str | None = None
    client_id: str | None = None
    client_secret_ref: str | None = None
    items_field: str = "items"
    next_cursor_field: str = "next_cursor"
    cursor_param: str = "cursor"
    since_param: str = "updated_since"
    limit_param: str = "limit"
    fields: list[str] = Field(default_factory=list)
    fields_param: str | None = None
    timeout_seconds: float = Field(default=30, gt=0, le=120)
    requests_per_second: float = Field(default=2, gt=0, le=100)
    max_response_bytes: int = Field(default=16777216, ge=1024, le=104857600)
    max_retries: int = Field(default=4, ge=0, le=8)
    max_pages: int = Field(default=10000, ge=1, le=100000)
    lookback_seconds: int = Field(default=300, ge=0, le=86400)

    @model_validator(mode="after")
    def valid_auth(self) -> "RestConfig":
        if not self.path.startswith("/") or self.path.startswith("//") or "?" in self.path:
            raise ValueError("REST path must be an absolute path without query")
        if self.auth == "bearer" and not self.secret_ref:
            raise ValueError("Bearer auth requires secret_ref")
        if self.auth == "oauth_client_credentials" and not all(
            [self.token_url, self.client_id, self.client_secret_ref]
        ):
            raise ValueError("OAuth requires token_url, client_id, client_secret_ref")
        if self.fields and not self.fields_param:
            raise ValueError("Field selection must be explicitly supported by the source")
        return self


class SheetsConfig(CommonConfig):
    kind: Literal["sheets"] = "sheets"
    spreadsheet_id: str = Field(pattern=r"^[a-zA-Z0-9_-]+$")
    ranges: list[str] = Field(min_length=1, max_length=100)
    auth: Literal["service_account", "oauth_token"] = "service_account"
    secret_ref: str
    max_snapshot_rows: int = Field(default=100000, ge=1, le=1000000)
    shop_field: str | None = None
    updated_field: str | None = None


class CsvConfig(CommonConfig):
    kind: Literal["csv"] = "csv"
    path: str
    encoding: Literal["utf-8", "utf-8-sig"] = "utf-8-sig"
    delimiter: Literal[",", ";", "\t", "|"] | None = None
    shop_field: str | None = None
    updated_field: str | None = None


class PostgresConfig(CommonConfig):
    kind: Literal["postgres"] = "postgres"
    secret_ref: str
    schema_name: str = "public"
    table: str
    updated_field: str = "updated_at"
    fields: list[str] = Field(min_length=1)
    query_timeout_ms: int = Field(default=15000, ge=100, le=120000)
    lookback_seconds: int = Field(default=300, ge=0, le=86400)

    @model_validator(mode="after")
    def required_fields(self) -> "PostgresConfig":
        for name in (self.key_field, self.updated_field, self.shop_field):
            if name and name not in self.fields:
                raise ValueError("Selected fields must contain key, timestamp and shop columns")
        return self


SourceConfig = Annotated[
    RestConfig | SheetsConfig | CsvConfig | PostgresConfig, Field(discriminator="kind")
]
config_adapter: TypeAdapter[RestConfig | SheetsConfig | CsvConfig | PostgresConfig] = TypeAdapter(
    SourceConfig  # type: ignore[arg-type]  # Pydantic accepts Annotated union schemas at runtime.
)
