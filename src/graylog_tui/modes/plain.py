from __future__ import annotations

import sys
import time

from graylog_tui.client import GraylogAuthError, GraylogClient, GraylogError, Message
from graylog_tui.formatter import plain_line


def run_plain(client: GraylogClient, poll_interval_ms: int, align: bool = False) -> None:
    seen_ids: set[str] = set()
    source_width = 0
    poll_s = poll_interval_ms / 1000.0

    try:
        while True:
            try:
                messages = client.fetch_messages()
            except GraylogAuthError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                sys.exit(1)
            except GraylogError as e:
                print(f"WARNING: {e}", file=sys.stderr)
                time.sleep(poll_s)
                continue

            new_messages = [m for m in messages if m.id not in seen_ids]
            new_messages.sort(key=lambda m: m.orig_timestamp)

            if align and new_messages:
                max_sw = max(len(m.source) for m in new_messages)
                if max_sw > source_width:
                    source_width = max_sw

            for msg in new_messages:
                seen_ids.add(msg.id)
                line = plain_line(msg, source_width if align else 0)
                sys.stdout.write(line + "\n")
                sys.stdout.flush()

            time.sleep(poll_s)
    except KeyboardInterrupt:
        sys.exit(0)
