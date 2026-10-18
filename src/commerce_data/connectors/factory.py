from commerce_data.config import Settings
from commerce_data.connectors.base import Connector
from commerce_data.connectors.contracts import (
    CsvConfig,
    PostgresConfig,
    RestConfig,
    SheetsConfig,
    config_adapter,
)
from commerce_data.connectors.postgres import PostgresConnector
from commerce_data.connectors.rest import RestConnector
from commerce_data.connectors.snapshot import CsvConnector, SheetsConnector


def build_connector(config: dict, settings: Settings) -> Connector:
    parsed = config_adapter.validate_python(config)
    if isinstance(parsed, RestConfig):
        return RestConnector(parsed, settings)
    if isinstance(parsed, CsvConfig):
        return CsvConnector(parsed, settings)
    if isinstance(parsed, SheetsConfig):
        return SheetsConnector(parsed, settings)
    if isinstance(parsed, PostgresConfig):
        return PostgresConnector(parsed, settings)
    raise ValueError("Unsupported connector")
