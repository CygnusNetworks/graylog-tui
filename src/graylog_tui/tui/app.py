from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical

from graylog_tui.client import GraylogAuthError, GraylogClient, GraylogError
from graylog_tui.tui.widgets import (
    MessageLogWidget,
    StreamsWidget,
    ThroughputWidget,
)


class GraylogDashboard(App[None]):
    CSS_PATH = Path(__file__).parent / "dashboard.tcss"

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
        with Horizontal():
            with Vertical(id="main-area"):
                with Horizontal(id="charts-row"):
                    yield ThroughputWidget("Stream", color="red", id="stream-chart")
                    yield ThroughputWidget("Total", color="green", id="total-chart")
                yield MessageLogWidget(id="msg-widget")
            yield StreamsWidget(id="streams-widget")

    def on_mount(self) -> None:
        self.run_worker(self._load_streams(), exclusive=True)
        self.set_interval(self._poll_s, self._poll)

    async def _load_streams(self) -> None:
        try:
            streams = await asyncio.to_thread(self._client.fetch_streams)
        except GraylogError as e:
            self.notify(f"Could not load streams: {e}", severity="warning", timeout=5)
            return
        sw = self.query_one("#streams-widget", StreamsWidget)
        sw.update_streams(streams, self._client.stream_id)

    async def _poll(self) -> None:
        if self._paused or not self._client.stream_id:
            return

        results = await asyncio.gather(
            asyncio.to_thread(self._client.fetch_messages),
            asyncio.to_thread(self._client.fetch_total_throughput),
            asyncio.to_thread(self._client.fetch_stream_throughput, self._client.stream_id),
            return_exceptions=True,
        )

        messages_result, total_tp_result, stream_tp_result = results

        if isinstance(messages_result, GraylogAuthError):
            self.notify("Authentication failed", severity="error", timeout=0)
            self.exit()
            return

        for result in results:
            if isinstance(result, GraylogError):
                self.notify(str(result), severity="warning", timeout=3)

        if isinstance(messages_result, list):
            new_messages = [m for m in messages_result if m.id not in self._seen_ids]
            new_messages.sort(key=lambda m: m.orig_timestamp)
            for msg in new_messages:
                self._seen_ids.add(msg.id)
            self.query_one("#msg-widget", MessageLogWidget).add_messages(new_messages)

        if isinstance(total_tp_result, float):
            self.query_one("#total-chart", ThroughputWidget).push_value(total_tp_result)

        if isinstance(stream_tp_result, float):
            self.query_one("#stream-chart", ThroughputWidget).push_value(stream_tp_result)

    def on_streams_widget_stream_selected(self, event: StreamsWidget.StreamSelected) -> None:
        stream = event.stream
        self._client.stream_id = stream.id
        self._seen_ids.clear()
        self.query_one("#msg-widget", MessageLogWidget).clear()
        self.query_one("#msg-widget", MessageLogWidget).set_stream(stream.title)
        self.query_one("#stream-chart", ThroughputWidget).clear()

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        status = "paused" if self._paused else "resumed"
        self.notify(f"Polling {status}", timeout=2)
