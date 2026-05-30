from __future__ import annotations

import sys

from rich.text import Text

from graylog_tui.client import Message


def detect_color() -> bool:
    return sys.stdout.isatty()


def plain_line(msg: Message, source_width: int = 0) -> str:
    source = msg.source.ljust(source_width) if source_width else msg.source
    return f"{msg.timestamp} - {source} - {msg.message}"


def format_message(msg: Message, source_width: int = 0, *, color: bool = True) -> str | Text:
    if not color:
        return plain_line(msg, source_width)
    source = msg.source.ljust(source_width) if source_width else msg.source
    t = Text()
    t.append(msg.timestamp, style="cyan")
    t.append(" - ")
    t.append(source, style="green")
    t.append(" - ")
    t.append(msg.message)
    return t
