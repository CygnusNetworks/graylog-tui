#!/usr/bin/env python3
"""Generate SVG screenshots of both TUI modes using mocked data."""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

from graylog_tui.client import GraylogStream, Message
from graylog_tui.tui.app import GraylogDashboard
from graylog_tui.tui.app_logs import LogsOnlyApp

OUT = Path(__file__).parent.parent / "docs"

HOSTS = ["web-01", "web-02", "app-01", "app-02", "db-01", "lb-01", "cache-01"]

LOG_LINES = [
    ("nginx",    6, 'GET /api/users 200 42ms 1.2kb'),
    ("nginx",    6, 'GET /api/products 200 18ms 8.4kb'),
    ("nginx",    6, 'POST /api/auth/login 201 95ms 512b'),
    ("nginx",    6, 'GET /health 200 1ms 32b'),
    ("nginx",    6, 'GET /static/app.js 304 2ms 0b'),
    ("nginx",    4, 'GET /api/orders/9921 404 12ms 128b'),
    ("nginx",    3, 'POST /api/checkout 502 5120ms 256b'),
    ("sshd",     6, 'Accepted publickey for deploy from 10.0.1.5 port 44821 ssh2'),
    ("sshd",     6, 'Accepted publickey for ubuntu from 10.0.2.11 port 52190 ssh2'),
    ("sshd",     4, 'Failed password for invalid user admin from 185.220.101.12 port 51234 ssh2'),
    ("sshd",     4, 'Failed password for invalid user root from 185.220.101.15 port 38741 ssh2'),
    ("systemd",  6, 'Started nginx.service'),
    ("systemd",  6, 'Reloaded nginx.service'),
    ("postgres", 6, 'duration: 8.1 ms  statement: SELECT * FROM users WHERE id = $1'),
    ("postgres", 6, 'duration: 42.3 ms  statement: SELECT COUNT(*) FROM orders WHERE created_at > $1'),
    ("postgres", 4, 'duration: 812.7 ms  statement: UPDATE sessions SET last_seen = NOW() WHERE token = $1'),
    ("app",      6, 'Request processed successfully'),
    ("app",      6, 'Cache hit ratio: 94.2%'),
    ("app",      6, 'Worker 3 processed 142 jobs'),
    ("app",      6, 'Healthcheck OK — db=4ms cache=0ms'),
    ("app",      5, 'Config reloaded from /etc/app/config.yml'),
    ("app",      4, 'Slow query detected (523ms), consider adding index'),
    ("app",      4, 'Retry 1/3 connecting to cache-01'),
    ("app",      3, 'Circuit breaker opened for payments-service'),
    ("app",      3, 'Job 4821 failed after 3 retries: connection refused'),
    ("cron",     6, '(/usr/bin/backup.sh) OK'),
    ("cron",     4, '(/usr/bin/send-reports.py) exit status 1'),
]


def make_messages(n: int = 30) -> list[Message]:
    now = datetime.now(timezone.utc)
    messages = []
    pool = LOG_LINES * 3
    random.shuffle(pool)
    for i, (svc, _level, text) in enumerate(pool[:n]):
        host = random.choice(HOSTS)
        ts = now - timedelta(seconds=(n - i) * 4)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        messages.append(Message(
            timestamp=ts_str,
            source=host,
            message=text,
            orig_timestamp=ts_str,
            id=f"msg-{i:04d}",
        ))
    return messages


def make_client(messages: list[Message]) -> MagicMock:
    client = MagicMock()
    client.stream_id = "000000000000000000000001"
    client.fetch_messages.return_value = messages
    client.fetch_total_throughput.return_value = 38.4
    client.fetch_stream_throughput.return_value = 12.1
    client.fetch_streams.return_value = [
        GraylogStream(id="000000000000000000000001", title="All messages"),
        GraylogStream(id="aabbcc0000000000000000001", title="Production errors"),
        GraylogStream(id="aabbcc0000000000000000002", title="Security events"),
        GraylogStream(id="aabbcc0000000000000000003", title="Nginx access"),
        GraylogStream(id="aabbcc0000000000000000004", title="Database slow queries"),
    ]
    return client


async def screenshot_logs_only(messages: list[Message]) -> None:
    client = make_client(messages)
    app = LogsOnlyApp(client, poll_interval_ms=50, align=True)
    async with app.run_test(size=(160, 42)) as pilot:
        await pilot.pause(1.5)
        path = OUT / "screenshot-logs.svg"
        app.save_screenshot(str(path))
        print(f"Saved {path}")


async def screenshot_dashboard(messages: list[Message]) -> None:
    client = make_client(messages)
    app = GraylogDashboard(client, poll_interval_ms=50, align=True)
    async with app.run_test(size=(160, 42)) as pilot:
        await pilot.pause(1.5)
        path = OUT / "screenshot-dashboard.svg"
        app.save_screenshot(str(path))
        print(f"Saved {path}")


async def main() -> None:
    random.seed(42)
    messages = make_messages(30)
    await screenshot_logs_only(messages)
    await screenshot_dashboard(messages)


asyncio.run(main())
