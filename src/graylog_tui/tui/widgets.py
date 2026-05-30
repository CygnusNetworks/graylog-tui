from __future__ import annotations

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
        self._data: list[float] = [0.0] * 60

    def compose(self) -> ComposeResult:
        yield Label(f"{self._title}: 0.0 msg/s", id="throughput-label")
        yield Sparkline(data=self._data, summary_function=max)

    def push_value(self, value: float) -> None:
        self._data.append(value)
        if len(self._data) > 60:
            self._data = self._data[-60:]
        self.query_one("#throughput-label", Label).update(
            f"{self._title}: {value:.1f} msg/s"
        )
        self.query_one(Sparkline).data = self._data

    def clear(self) -> None:
        self._data = [0.0] * 60
        self.query_one(Sparkline).data = self._data


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
        for stream in streams:
            item = ListItem(Label(stream.title[:22]), id=f"stream-{stream.id}")
            lv.append(item)

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

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._source_width = 0

    def compose(self) -> ComposeResult:
        yield RichLog(id="msg-log", highlight=False, markup=False, auto_scroll=True)

    def add_messages(self, messages: list[GraylogMessage]) -> None:
        if not messages:
            return
        max_sw = max(len(m.source) for m in messages)
        if max_sw > self._source_width:
            self._source_width = max_sw
        log = self.query_one("#msg-log", RichLog)
        for msg in messages:
            rendered = format_message(msg, self._source_width, color=True)
            log.write(rendered)

    def clear(self) -> None:
        self._source_width = 0
        self.query_one("#msg-log", RichLog).clear()

    def set_stream(self, title: str) -> None:
        self.border_title = f"Messages — {title}"
