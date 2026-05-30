from __future__ import annotations

import sys
import threading
import time
from collections import deque

import readchar
from rich.console import Console

from graylog_tui.client import GraylogAuthError, GraylogClient, GraylogError
from graylog_tui.formatter import format_message

PAUSE_BUFFER_MAX = 20


def _interruptible_sleep(stop: threading.Event, duration: float, step: float = 0.05) -> None:
    elapsed = 0.0
    while elapsed < duration and not stop.is_set():
        time.sleep(step)
        elapsed += step


def run_tail(client: GraylogClient, poll_interval_ms: int, align: bool = False) -> None:
    console = Console(stderr=False)
    seen_ids: set[str] = set()
    source_width = 0
    poll_s = poll_interval_ms / 1000.0

    paused = threading.Event()
    stop = threading.Event()
    pause_buffer: deque[object] = deque(maxlen=PAUSE_BUFFER_MAX)

    def keyboard_thread() -> None:
        while not stop.is_set():
            try:
                key = readchar.readkey()
            except Exception:
                break
            if key == " ":
                if paused.is_set():
                    paused.clear()
                    buffered = list(pause_buffer)
                    pause_buffer.clear()
                    if buffered:
                        console.print(f"[dim]--- {len(buffered)} buffered messages ---[/dim]")
                        for line in buffered:
                            console.print(line)
                else:
                    paused.set()
                    console.print("[dim]--- paused (press SPACE to resume) ---[/dim]")
            elif key in (readchar.key.ESC, "q", "\x03"):
                stop.set()
                break

    kb_thread = threading.Thread(target=keyboard_thread, daemon=True)
    kb_thread.start()

    try:
        while not stop.is_set():
            try:
                messages = client.fetch_messages()
            except GraylogAuthError as e:
                console.print(f"[red]ERROR:[/red] {e}", highlight=False)
                stop.set()
                sys.exit(1)
            except GraylogError as e:
                console.print(f"[yellow]WARNING:[/yellow] {e}", highlight=False)
                _interruptible_sleep(stop, poll_s)
                continue

            new_messages = [m for m in messages if m.id not in seen_ids]
            new_messages.sort(key=lambda m: m.orig_timestamp)

            if align and new_messages:
                max_sw = max(len(m.source) for m in new_messages)
                if max_sw > source_width:
                    source_width = max_sw

            for msg in new_messages:
                seen_ids.add(msg.id)
                rendered = format_message(msg, source_width if align else 0, color=True)
                if paused.is_set():
                    pause_buffer.append(rendered)
                else:
                    console.print(rendered)

            _interruptible_sleep(stop, poll_s)
    except KeyboardInterrupt:
        stop.set()
        sys.exit(0)

    sys.exit(0)
