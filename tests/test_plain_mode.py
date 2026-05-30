from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from graylog_tui.client import GraylogAuthError, GraylogConnectionError, Message
from graylog_tui.modes.plain import run_plain


def make_msg(id: str, source: str = "host1", msg: str = "test message") -> Message:
    return Message(
        timestamp="2026-01-01T00:00:00Z",
        source=source,
        message=msg,
        orig_timestamp="2026-01-01T00:00:00Z",
        id=id,
    )


def test_plain_mode_prints_messages(capsys: pytest.CaptureFixture[str]) -> None:
    client = MagicMock()
    client.fetch_messages.side_effect = [
        [make_msg("id1", msg="first message")],
        KeyboardInterrupt(),
    ]
    with pytest.raises(SystemExit) as exc:
        run_plain(client, poll_interval_ms=0)
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "first message" in captured.out
    assert "\x1b" not in captured.out


def test_plain_mode_deduplicates(capsys: pytest.CaptureFixture[str]) -> None:
    client = MagicMock()
    msg = make_msg("same-id", msg="only once")
    client.fetch_messages.side_effect = [
        [msg],
        [msg],
        KeyboardInterrupt(),
    ]
    with pytest.raises(SystemExit):
        run_plain(client, poll_interval_ms=0)
    captured = capsys.readouterr()
    assert captured.out.count("only once") == 1


def test_plain_mode_auth_error_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    client = MagicMock()
    client.fetch_messages.side_effect = GraylogAuthError("bad credentials")
    with pytest.raises(SystemExit) as exc:
        run_plain(client, poll_interval_ms=0)
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "ERROR" in captured.err


def test_plain_mode_connection_error_continues(capsys: pytest.CaptureFixture[str]) -> None:
    client = MagicMock()
    client.fetch_messages.side_effect = [
        GraylogConnectionError("timeout"),
        [make_msg("id1", msg="recovered")],
        KeyboardInterrupt(),
    ]
    with pytest.raises(SystemExit) as exc:
        run_plain(client, poll_interval_ms=0)
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "recovered" in captured.out
    assert "WARNING" in captured.err


def test_plain_mode_align_pads_source(capsys: pytest.CaptureFixture[str]) -> None:
    client = MagicMock()
    client.fetch_messages.side_effect = [
        [make_msg("id1", source="short"), make_msg("id2", source="muchlonger")],
        KeyboardInterrupt(),
    ]
    with pytest.raises(SystemExit):
        run_plain(client, poll_interval_ms=0, align=True)
    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()
    assert len(lines) == 2
    sources = [line.split(" - ")[1] for line in lines]
    assert all(len(s) == len(sources[0]) for s in sources)
