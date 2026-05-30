from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


class GraylogError(Exception):
    pass


class GraylogConnectionError(GraylogError):
    pass


class GraylogAuthError(GraylogError):
    pass


class GraylogAPIError(GraylogError):
    pass


@dataclass
class Message:
    timestamp: str
    source: str
    message: str
    orig_timestamp: str
    id: str = field(default="")

    def __post_init__(self) -> None:
        if not self.id:
            snippet = self.message[:32].replace(":", "_")
            self.id = f"{self.orig_timestamp}:{self.source}:{snippet}"


@dataclass
class GraylogStream:
    id: str
    title: str


class GraylogClient:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        insecure: bool = False,
        query: str = "*",
        fields: str = "timestamp,message,source,orig_timestamp",
        range_seconds: int = 300,
    ) -> None:
        self.stream_id: str | None = None
        self._query = query
        self._fields = fields
        self._range = range_seconds
        self._client = httpx.Client(
            base_url=host,
            auth=(username, password),
            headers={
                "Accept": "application/json",
                "X-Requested-By": "graylog",
            },
            timeout=10.0,
            verify=not insecure,
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            resp = self._client.get(path, params=params)
        except httpx.ConnectError as e:
            raise GraylogConnectionError(f"Cannot connect to Graylog: {e}") from e
        except httpx.TimeoutException as e:
            raise GraylogConnectionError(f"Graylog request timed out: {e}") from e
        except httpx.RequestError as e:
            raise GraylogConnectionError(f"Graylog request failed: {e}") from e

        if resp.status_code == 401:
            raise GraylogAuthError("Graylog authentication failed (check username/password)")
        if resp.status_code >= 400:
            raise GraylogAPIError(f"Graylog API error {resp.status_code}: {resp.text[:200]}")

        content_type = resp.headers.get("content-type", "")
        if "application/json" not in content_type:
            raise GraylogAPIError(
                f"Graylog returned non-JSON response (content-type: {content_type!r}). "
                "Check the --host URL and credentials."
            )

        try:
            return resp.json()
        except Exception as e:
            raise GraylogAPIError(f"Graylog returned invalid JSON: {e}") from e

    def fetch_streams(self) -> list[GraylogStream]:
        data = self._get("streams")
        streams = data.get("streams", [])
        return sorted(
            [GraylogStream(id=s["id"], title=s["title"]) for s in streams],
            key=lambda s: s.title.lower(),
        )

    def fetch_messages(self) -> list[Message]:
        if not self.stream_id:
            return []
        params: dict[str, Any] = {
            "range": self._range,
            "query": self._query,
            "filter": f"streams:{self.stream_id}",
            "fields": self._fields,
            "limit": 100,
            "sort": "timestamp:desc",
        }
        data = self._get("search/universal/relative", params=params)
        messages = []
        for m in data.get("messages", []):
            msg = m.get("message", {})
            gl2_id = msg.get("gl2_message_id", "")
            messages.append(
                Message(
                    timestamp=msg.get("timestamp", ""),
                    source=msg.get("source", ""),
                    message=msg.get("message", ""),
                    orig_timestamp=msg.get("orig_timestamp", msg.get("timestamp", "")),
                    id=gl2_id,
                )
            )
        return messages

    def fetch_total_throughput(self) -> float:
        data = self._get("system/throughput")
        return float(data.get("throughput", 0))

    def fetch_stream_throughput(self, stream_id: str) -> float:
        metric_name = (
            f"org.graylog2.plugin.streams.Stream.{stream_id}.incomingMessages.1-sec-rate"
        )
        try:
            data = self._get(f"system/metrics/{metric_name}")
            return float(data.get("metric", {}).get("value", 0))
        except GraylogAPIError:
            try:
                data = self._get(f"streams/{stream_id}/throughput")
                return float(data.get("throughput", 0))
            except GraylogAPIError:
                return 0.0

    def close(self) -> None:
        self._client.close()
