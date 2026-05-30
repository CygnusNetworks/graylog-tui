from __future__ import annotations

from collections import deque

from textual.app import ComposeResult
from textual.message import Message as TextualMessage
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView, RichLog, Sparkline

from graylog_tui.client import GraylogStream
from graylog_tui.client import Message as GraylogMessage
from graylog_tui.formatter import format_message


class ThroughputWidget(Widget):
    DEFAULT_CSS = """
    ThroughputWidget {
        height: 100%;
        border: solid $primary;
    }
    ThroughputWidget Label {
        height: 1;
        padding: 0 1;
    }
    ThroughputWidget Sparkline {
        height: 1fr;
    }
    """

    def __init__(self, title: str, color: str = "green", **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._title = title
        self._color = color
        self._data: deque[float] = deque([0.0] * 60, maxlen=60)

    def compose(self) -> ComposeResult:
        yield Label(f"{self._title}: 0.0 msg/s", id="throughput-label")
        yield Sparkline(data=list(self._data), summary_function=max)

    def push_value(self, value: float) -> None:
        self._data.append(value)
        self.query_one("#throughput-label", Label).update(
            f"{self._title}: {value:.1f} msg/s"
        )
        self.query_one(Sparkline).data = list(self._data)

    def clear(self) -> None:
        self._data = deque([0.0] * 60, maxlen=60)
        self.query_one(Sparkline).data = list(self._data)


class StreamsWidget(Widget):
    class StreamSelected(TextualMessage):
        def __init__(self, stream: GraylogStream) -> None:
            super().__init__()
            self.stream = stream

    DEFAULT_CSS = """
    StreamsWidget {
        width: 24;
        border: solid $accent;
    }
    StreamsWidget Label {
        height: 1;
        padding: 0 1;
        background: $accent;
        color: $text;
        width: 100%;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._streams: list[GraylogStream] = []

    def compose(self) -> ComposeResult:
        yield Label("Streams")
        yield ListView(id="stream-list")

    def update_streams(self, streams: list[GraylogStream], active_id: str | None = None) -> None:
        self._streams = streams
        lv = self.query_one("#stream-list", ListView)
        lv.clear()
        active_index = None
        for i, stream in enumerate(streams):
            item = ListItem(Label(stream.title[:22]), id=f"stream-{stream.id}")
            lv.append(item)
            if stream.id == active_id:
                active_index = i
        if active_index is not None:
            lv.index = active_index

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item.id:
            stream_id = event.item.id.removeprefix("stream-")
            for stream in self._streams:
                if stream.id == stream_id:
                    self.post_message(self.StreamSelected(stream))
                    break


class MessageLogWidget(Widget):
    DEFAULT_CSS = """
    MessageLogWidget {
        height: 1fr;
        border: solid $surface-lighten-3;
    }
    MessageLogWidget RichLog {
        height: 1fr;
    }
    """

    def __init__(self, align: bool = True, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._align = align
        self._source_width = 0

    def compose(self) -> ComposeResult:
        yield RichLog(id="msg-log", highlight=False, markup=False, auto_scroll=True)

    def add_messages(self, messages: list[GraylogMessage]) -> None:
        if not messages:
            return
        if self._align:
            max_sw = max(len(m.source) for m in messages)
            if max_sw > self._source_width:
                self._source_width = max_sw
        log = self.query_one("#msg-log", RichLog)
        for msg in messages:
            rendered = format_message(msg, self._source_width if self._align else 0, color=True)
            log.write(rendered)

    def clear(self) -> None:
        self._source_width = 0
        self.query_one("#msg-log", RichLog).clear()

    def set_stream(self, title: str) -> None:
        self.border_title = f"Messages — {title}"
