from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding

from graylog_tui.client import GraylogAuthError, GraylogClient, GraylogError
from graylog_tui.tui.widgets import MessageLogWidget


class LogsOnlyApp(App[None]):
    CSS_PATH = Path(__file__).parent / "logs_only.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("escape", "quit", "Quit"),
        Binding("space", "toggle_pause", "Pause/Resume"),
    ]

    TITLE = "Graylog Dashboard"

    def __init__(self, client: GraylogClient, poll_interval_ms: int, align: bool = False) -> None:
        super().__init__()
        self._client = client
        self._poll_s = poll_interval_ms / 1000.0
        self._align = align
        self._seen_ids: set[str] = set()
        self._paused = False

    def compose(self) -> ComposeResult:
        yield MessageLogWidget(align=self._align, id="msg-widget")

    def on_mount(self) -> None:
        widget = self.query_one(MessageLogWidget)
        if self._client.stream_id:
            widget.border_title = f"Messages — stream {self._client.stream_id}"
        self.set_interval(self._poll_s, self._poll)

    async def _poll(self) -> None:
        if self._paused:
            return
        try:
            messages = await asyncio.to_thread(self._client.fetch_messages)
        except GraylogAuthError as e:
            self.notify(str(e), severity="error", timeout=5)
            self.exit()
            return
        except GraylogError as e:
            self.notify(str(e), severity="warning", timeout=3)
            return

        new_messages = [m for m in messages if m.id not in self._seen_ids]
        new_messages.sort(key=lambda m: m.orig_timestamp)
        for msg in new_messages:
            self._seen_ids.add(msg.id)

        widget = self.query_one(MessageLogWidget)
        widget.add_messages(new_messages)

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        status = "paused" if self._paused else "resumed"
        self.notify(f"Log tail {status}", timeout=2)
