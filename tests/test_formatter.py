from rich.text import Text

from graylog_tui.client import Message
from graylog_tui.formatter import format_message, plain_line


def make_msg() -> Message:
    return Message(
        timestamp="2026-01-01T00:00:00Z",
        source="host1",
        message="connection established",
        orig_timestamp="2026-01-01T00:00:00Z",
        id="abc",
    )


def test_plain_line_no_ansi() -> None:
    result = plain_line(make_msg())
    assert "\x1b" not in result
    assert result == "2026-01-01T00:00:00Z - host1 - connection established"


def test_plain_line_with_source_width() -> None:
    result = plain_line(make_msg(), source_width=20)
    assert "host1               " in result


def test_format_message_color_returns_rich_text() -> None:
    result = format_message(make_msg(), color=True)
    assert isinstance(result, Text)
    plain = result.plain
    assert "host1" in plain
    assert "connection established" in plain
    assert "2026-01-01T00:00:00Z" in plain


def test_format_message_color_false_returns_string() -> None:
    result = format_message(make_msg(), color=False)
    assert isinstance(result, str)
    assert "\x1b" not in result


def test_format_message_color_segments() -> None:
    result = format_message(make_msg(), color=True)
    assert isinstance(result, Text)
    styles = {span.style for span in result._spans}
    assert "cyan" in styles
    assert "green" in styles


def test_format_message_source_width_padding() -> None:
    result = format_message(make_msg(), source_width=20, color=False)
    assert isinstance(result, str)
    assert "host1               " in result
