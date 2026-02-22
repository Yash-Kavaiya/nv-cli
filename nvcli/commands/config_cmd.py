"""Config commands: show current configuration."""
from __future__ import annotations

import typer
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

from nvcli.config import load_config

config_app = typer.Typer(help="View and manage nvcli configuration.")


@config_app.command("show")
def show() -> None:
    """Show current configuration (API key masked)."""
    config = load_config()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    api_key_display = "not set"
    if config.api_key:
        api_key_display = (
            f"nvapi-...{config.api_key[-4:]}" if len(config.api_key) > 10 else "****"
        )

    table.add_row("api_key", api_key_display)
    table.add_row("base_url", config.base_url)
    table.add_row("model", config.model)
    table.add_row("temperature", str(config.temperature))
    table.add_row("max_tokens", str(config.max_tokens))
    table.add_row("session_dir", str(config.session_dir))
    table.add_row("dry_run", str(config.dry_run))
    table.add_row(
        "command_allowlist",
        str(config.command_allowlist) if config.command_allowlist else "[]",
    )

    rprint(Panel(table, title="[bold]nvcli configuration[/bold]", border_style="blue"))
