import httpx
import pytest
import respx

from graylog_tui.client import (
    GraylogAPIError,
    GraylogAuthError,
    GraylogClient,
    GraylogConnectionError,
    Message,
)

BASE = "https://graylog.example.com"


def make_client(**kwargs: object) -> GraylogClient:
    return GraylogClient(host=BASE, username="admin", password="secret", **kwargs)  # type: ignore[arg-type]


@respx.mock
def test_fetch_streams_returns_sorted_list() -> None:
    respx.get(f"{BASE}/streams").mock(
        return_value=httpx.Response(
            200,
            json={
                "streams": [
                    {"id": "2", "title": "Zebra"},
                    {"id": "1", "title": "Alpha"},
                ]
            },
        )
    )
    client = make_client()
    streams = client.fetch_streams()
    assert len(streams) == 2
    assert streams[0].title == "Alpha"
    assert streams[1].title == "Zebra"


@respx.mock
def test_fetch_messages_returns_parsed_messages() -> None:
    respx.get(f"{BASE}/search/universal/relative").mock(
        return_value=httpx.Response(
            200,
            json={
                "messages": [
                    {
                        "message": {
                            "timestamp": "2026-01-01T00:00:00.000Z",
                            "source": "host1",
                            "message": "hello world",
                            "orig_timestamp": "2026-01-01T00:00:00.000Z",
                            "gl2_message_id": "abc123",
                        }
                    }
                ]
            },
        )
    )
    client = make_client()
    client.stream_id = "stream1"
    msgs = client.fetch_messages()
    assert len(msgs) == 1
    assert msgs[0].source == "host1"
    assert msgs[0].message == "hello world"
    assert msgs[0].id == "abc123"


@respx.mock
def test_fetch_messages_empty_stream_id_returns_empty() -> None:
    client = make_client()
    assert client.fetch_messages() == []


@respx.mock
def test_fetch_messages_uses_fallback_id() -> None:
    respx.get(f"{BASE}/search/universal/relative").mock(
        return_value=httpx.Response(
            200,
            json={
                "messages": [
                    {
                        "message": {
                            "timestamp": "2026-01-01T00:00:01.000Z",
                            "source": "host2",
                            "message": "no gl2 id here",
                            "orig_timestamp": "2026-01-01T00:00:01.000Z",
                        }
                    }
                ]
            },
        )
    )
    client = make_client()
    client.stream_id = "stream1"
    msgs = client.fetch_messages()
    assert msgs[0].id.startswith("2026-01-01T00:00:01.000Z:host2:")


@respx.mock
def test_fetch_total_throughput() -> None:
    respx.get(f"{BASE}/system/throughput").mock(
        return_value=httpx.Response(200, json={"throughput": 42.5})
    )
    client = make_client()
    assert client.fetch_total_throughput() == 42.5


@respx.mock
def test_http_401_raises_auth_error() -> None:
    respx.get(f"{BASE}/streams").mock(return_value=httpx.Response(401))
    client = make_client()
    with pytest.raises(GraylogAuthError):
        client.fetch_streams()


@respx.mock
def test_http_500_raises_api_error() -> None:
    respx.get(f"{BASE}/streams").mock(return_value=httpx.Response(500, text="Internal error"))
    client = make_client()
    with pytest.raises(GraylogAPIError, match="500"):
        client.fetch_streams()


@respx.mock
def test_connection_error_raises_connection_error() -> None:
    respx.get(f"{BASE}/streams").mock(side_effect=httpx.ConnectError("refused"))
    client = make_client()
    with pytest.raises(GraylogConnectionError, match="connect"):
        client.fetch_streams()


def test_message_dedup_id_generated() -> None:
    msg = Message(
        timestamp="ts",
        source="src",
        message="hello world",
        orig_timestamp="ots",
    )
    assert msg.id == "ots:src:hello world"


def test_message_explicit_id_preserved() -> None:
    msg = Message(
        timestamp="ts",
        source="src",
        message="hello",
        orig_timestamp="ots",
        id="explicit-id",
    )
    assert msg.id == "explicit-id"
