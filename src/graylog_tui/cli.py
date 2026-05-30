from __future__ import annotations

import sys
from pathlib import Path

import typer

from graylog_tui import __version__
from graylog_tui.client import GraylogAuthError, GraylogClient, GraylogError
from graylog_tui.config import (
    DEFAULT_FIELDS,
    DEFAULT_POLL_INTERVAL_MS,
    DEFAULT_RANGE_SECONDS,
    ConfigError,
    ConfigFileNotFoundError,
    GraylogConfig,
    load_config,
)
from graylog_tui.modes.plain import run_plain

app = typer.Typer(name="graylog-tui", add_completion=False, pretty_exceptions_enable=False)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"graylog-tui {__version__}")
        raise typer.Exit()


def _resolve_stream(
    client: GraylogClient, stream_id: str | None, stream_title: str | None
) -> str | None:
    if stream_id:
        return stream_id
    if not stream_title:
        return None
    try:
        streams = client.fetch_streams()
    except GraylogAuthError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from None
    except GraylogError as e:
        typer.echo(f"ERROR fetching streams: {e}", err=True)
        raise typer.Exit(1) from None

    title_lower = stream_title.lower()
    for stream in streams:
        if stream.title.lower() == title_lower:
            return stream.id

    matches = [s for s in streams if s.title.lower().startswith(title_lower)]
    if len(matches) == 1:
        return matches[0].id
    if len(matches) > 1:
        typer.echo(
            f"ERROR: ambiguous stream title '{stream_title}', matches: "
            + ", ".join(s.title for s in matches),
            err=True,
        )
        raise typer.Exit(1)

    typer.echo(f"ERROR: no stream found matching '{stream_title}'", err=True)
    raise typer.Exit(1)


@app.command()
def main(
    host: str | None = typer.Option(None, "--host", "-H", help="Graylog base URL"),
    stream_id: str | None = typer.Option(None, "--stream-id", "-s", help="Stream UUID"),
    stream_title: str | None = typer.Option(None, "--stream-title", help="Stream title (fuzzy)"),
    gui: bool = typer.Option(
        False, "--gui", "-g", help="Full dashboard TUI with charts and stream selector"
    ),
    align: bool = typer.Option(False, "--align", help="Pad source hostnames to equal width"),
    poll_interval: int | None = typer.Option(None, "--poll-interval", help="Poll frequency ms"),
    insecure: bool = typer.Option(False, "--insecure", help="Skip TLS verification"),
    config_file: Path | None = typer.Option(None, "--config", help="Config file path"),
    version: bool | None = typer.Option(
        None, "--version", "-v", callback=_version_callback, is_eager=True, help="Show version"
    ),
) -> None:
    cfg: GraylogConfig | None = None
    try:
        cfg = load_config(config_file)
    except ConfigFileNotFoundError as e:
        if config_file is not None:
            typer.echo(f"ERROR: {e}", err=True)
            raise typer.Exit(1) from None
        # Default config absent — CLI args may supply what's needed
    except ConfigError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from None

    effective_host = host or (cfg.host if cfg else None)
    if not effective_host:
        typer.echo("ERROR: --host is required (or set 'host' in config file)", err=True)
        raise typer.Exit(1)

    effective_username = cfg.username if cfg else ""
    effective_password = cfg.password if cfg else ""
    if not effective_username or not effective_password:
        typer.echo("ERROR: username and password must be set in config file", err=True)
        raise typer.Exit(1)

    effective_poll_ms = poll_interval or (cfg.poll_interval_ms if cfg else DEFAULT_POLL_INTERVAL_MS)
    effective_insecure = insecure or (cfg.insecure if cfg else False)

    client = GraylogClient(
        host=effective_host,
        username=effective_username,
        password=effective_password,
        insecure=effective_insecure,
        query=cfg.query if cfg else "*",
        fields=cfg.fields if cfg else DEFAULT_FIELDS,
        range_seconds=cfg.range_seconds if cfg else DEFAULT_RANGE_SECONDS,
    )

    effective_stream_id = _resolve_stream(
        client,
        stream_id,
        stream_title or (cfg.stream_title if cfg else None),
    )
    client.stream_id = effective_stream_id

    # Stream required unless --gui (which has an interactive stream selector)
    if not gui and not client.stream_id:
        typer.echo(
            "ERROR: --stream-id or --stream-title required (or use --gui to select interactively)",
            err=True,
        )
        raise typer.Exit(1)

    try:
        if gui:
            from graylog_tui.tui.app import GraylogDashboard
            GraylogDashboard(client, effective_poll_ms, align=align).run()
        elif sys.stdout.isatty():
            from graylog_tui.tui.app_logs import LogsOnlyApp
            LogsOnlyApp(client, effective_poll_ms, align=align).run()
        else:
            run_plain(client, effective_poll_ms, align=align)
    finally:
        client.close()


def entry() -> None:
    app()
