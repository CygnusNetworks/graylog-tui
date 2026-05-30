from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path.home() / ".graylog_tui"

DEFAULT_FIELDS = "timestamp,message,source,orig_timestamp"
DEFAULT_RANGE_SECONDS = 300
DEFAULT_POLL_INTERVAL_MS = 1000


class ConfigError(Exception):
    pass


class ConfigFileNotFoundError(ConfigError):
    pass


@dataclass
class GraylogConfig:
    host: str | None
    username: str
    password: str
    poll_interval_ms: int = DEFAULT_POLL_INTERVAL_MS
    insecure: bool = False
    stream_title: str | None = None
    query: str = "*"
    fields: str = DEFAULT_FIELDS
    range_seconds: int = DEFAULT_RANGE_SECONDS


def load_config(path: Path | None = None) -> GraylogConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    try:
        raw = config_path.read_text()
    except FileNotFoundError:
        raise ConfigFileNotFoundError(f"Config file not found: {config_path}") from None
    except OSError as e:
        raise ConfigError(f"Cannot read config file {config_path}: {e}") from e

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {config_path}: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"Config file {config_path} must contain a YAML mapping")

    for key in ("username", "password"):
        if key not in data:
            raise ConfigError(f"Missing required key '{key}' in {config_path}")

    raw_host = data.get("host")
    return GraylogConfig(
        host=str(raw_host).rstrip("/") if raw_host else None,
        username=str(data["username"]),
        password=str(data["password"]),
        poll_interval_ms=int(
            data.get("poll-interval") or data.get("poll_interval_ms") or DEFAULT_POLL_INTERVAL_MS
        ),
        insecure=bool(data.get("insecure", False)),
        stream_title=data.get("stream-title") or data.get("stream_title"),
        query=str(data.get("query", "*")),
        fields=str(data.get("fields", DEFAULT_FIELDS)),
        range_seconds=int(data.get("range", DEFAULT_RANGE_SECONDS)),
    )
