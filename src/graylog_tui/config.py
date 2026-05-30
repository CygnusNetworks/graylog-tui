from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


DEFAULT_CONFIG_PATH = Path.home() / ".graylog_tui"


class ConfigError(Exception):
    pass


@dataclass
class GraylogConfig:
    host: str | None
    username: str
    password: str
    poll_interval_ms: int = 1000
    insecure: bool = False
    stream_title: str | None = None
    query: str = "*"
    fields: str = "timestamp,message,source,orig_timestamp"
    range_seconds: int = 300


def load_config(path: Path | None = None) -> GraylogConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    try:
        raw = config_path.read_text()
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {config_path}")
    except OSError as e:
        raise ConfigError(f"Cannot read config file {config_path}: {e}")

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {config_path}: {e}")

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
        poll_interval_ms=int(data.get("poll-interval", data.get("poll_interval_ms", 1000))),
        insecure=bool(data.get("insecure", False)),
        stream_title=data.get("stream-title") or data.get("stream_title"),
        query=str(data.get("query", "*")),
        fields=str(data.get("fields", "timestamp,message,source,orig_timestamp")),
        range_seconds=int(data.get("range", 300)),
    )
