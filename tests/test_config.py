from pathlib import Path

import pytest

from graylog_tui.config import ConfigError, ConfigFileNotFoundError, load_config


def write_config(tmp_path: Path, content: str) -> Path:
    p = tmp_path / ".graylog_tui"
    p.write_text(content)
    return p


def test_load_config_happy_path(tmp_path: Path) -> None:
    p = write_config(
        tmp_path, "host: https://graylog.example.com\nusername: admin\npassword: secret\n"
    )
    cfg = load_config(p)
    assert cfg.host == "https://graylog.example.com"
    assert cfg.username == "admin"
    assert cfg.password == "secret"
    assert cfg.poll_interval_ms == 1000
    assert cfg.insecure is False
    assert cfg.stream_title is None


def test_load_config_strips_trailing_slash(tmp_path: Path) -> None:
    p = write_config(tmp_path, "host: https://graylog.example.com/\nusername: u\npassword: p\n")
    cfg = load_config(p)
    assert cfg.host == "https://graylog.example.com"


def test_load_config_optional_fields(tmp_path: Path) -> None:
    p = write_config(
        tmp_path,
        "host: https://gl.local\nusername: u\npassword: p\n"
        "poll-interval: 2000\ninsecure: true\nstream-title: My Stream\n",
    )
    cfg = load_config(p)
    assert cfg.poll_interval_ms == 2000
    assert cfg.insecure is True
    assert cfg.stream_title == "My Stream"


def test_load_config_file_not_found() -> None:
    with pytest.raises(ConfigFileNotFoundError, match="not found"):
        load_config(Path("/nonexistent/path/.graylog_tui"))


def test_load_config_host_optional(tmp_path: Path) -> None:
    p = write_config(tmp_path, "username: admin\npassword: secret\n")
    cfg = load_config(p)
    assert cfg.host is None
    assert cfg.username == "admin"


def test_load_config_missing_username(tmp_path: Path) -> None:
    p = write_config(tmp_path, "host: https://gl.local\npassword: secret\n")
    with pytest.raises(ConfigError, match="username"):
        load_config(p)


def test_load_config_missing_password(tmp_path: Path) -> None:
    p = write_config(tmp_path, "host: https://gl.local\nusername: admin\n")
    with pytest.raises(ConfigError, match="password"):
        load_config(p)


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    p = write_config(tmp_path, "host: [\nbroken yaml")
    with pytest.raises(ConfigError, match="YAML"):
        load_config(p)


def test_load_config_not_a_mapping(tmp_path: Path) -> None:
    p = write_config(tmp_path, "- just a list\n")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(p)
