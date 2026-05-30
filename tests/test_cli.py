from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from graylog_tui.cli import app
from graylog_tui.client import GraylogStream

runner = CliRunner()


def make_config_file(tmp_path: Path, host: str = "https://gl.local") -> Path:
    p = tmp_path / ".graylog_tui"
    p.write_text(f"host: {host}\nusername: admin\npassword: secret\n")
    return p


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "graylog-tui" in result.output


def test_missing_host_exits_with_error(tmp_path: Path) -> None:
    result = runner.invoke(app, ["--config", str(tmp_path / "nonexistent")])
    assert result.exit_code == 1
    assert "host" in result.output.lower()


def test_plain_mode_when_not_tty(tmp_path: Path) -> None:
    # CliRunner stdout is not a tty → plain mode
    cfg = make_config_file(tmp_path)
    with (
        patch("graylog_tui.cli.run_plain") as mock_plain,
        patch("graylog_tui.cli.GraylogClient"),
    ):
        mock_plain.side_effect = SystemExit(0)
        result = runner.invoke(app, ["--config", str(cfg), "--stream-id", "s1"])
        mock_plain.assert_called_once()


def test_logs_only_tui_when_tty(tmp_path: Path) -> None:
    cfg = make_config_file(tmp_path)
    mock_app = MagicMock()
    with (
        patch("graylog_tui.cli.GraylogClient"),
        patch("graylog_tui.cli.sys") as mock_sys,
        patch("graylog_tui.tui.app_logs.LogsOnlyApp", return_value=mock_app),
    ):
        mock_sys.stdout.isatty.return_value = True
        mock_sys.exit = MagicMock(side_effect=SystemExit)
        runner.invoke(app, ["--config", str(cfg), "--stream-id", "s1"])
        mock_app.run.assert_called_once()


def test_gui_flag_dispatches_to_dashboard(tmp_path: Path) -> None:
    cfg = make_config_file(tmp_path)
    mock_app = MagicMock()
    with (
        patch("graylog_tui.cli.GraylogClient"),
        patch("graylog_tui.tui.app.GraylogDashboard", return_value=mock_app),
    ):
        mock_app.run.return_value = None
        runner.invoke(app, ["--config", str(cfg), "--gui"])


def test_no_stream_id_exits_without_gui(tmp_path: Path) -> None:
    cfg = make_config_file(tmp_path)
    with patch("graylog_tui.cli.GraylogClient"):
        result = runner.invoke(app, ["--config", str(cfg)])
    assert result.exit_code == 1
    assert "stream" in result.output.lower()


def test_stream_title_resolved(tmp_path: Path) -> None:
    cfg = make_config_file(tmp_path)
    mock_client = MagicMock()
    mock_client.fetch_streams.return_value = [GraylogStream(id="abc123", title="My Stream")]
    mock_client.stream_id = None

    with (
        patch("graylog_tui.cli.GraylogClient", return_value=mock_client),
        patch("graylog_tui.cli.run_plain") as mock_plain,
    ):
        mock_plain.side_effect = SystemExit(0)
        runner.invoke(app, ["--config", str(cfg), "--stream-title", "My Stream"])
        assert mock_client.stream_id == "abc123"
