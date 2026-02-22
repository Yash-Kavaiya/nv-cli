"""Models commands: list available NVIDIA models."""
from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.table import Table
from rich.console import Console

from nvcli.config import load_config
from nvcli.nvidia_client import NvidiaClient

models_app = typer.Typer(help="Manage and list available NVIDIA models.")
console = Console()


@models_app.command("list")
def list_models() -> None:
    """List all models available on the configured NVIDIA endpoint."""
    config = load_config()

    if not config.api_key:
        rprint(
            "[red]Error: No API key configured.[/red] "
            "Run [bold]nv auth set-key[/bold] to add your key."
        )
        raise typer.Exit(code=1)

    rprint("[dim]Fetching available models…[/dim]")

    client = NvidiaClient(config)
    try:
        model_ids = asyncio.run(client.list_models())
    except RuntimeError as exc:
        rprint(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    if not model_ids:
        rprint("[yellow]No models returned from the API.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta", show_lines=False)
    table.add_column("#", style="dim", width=5, justify="right")
    table.add_column("Model ID", style="cyan")

    for idx, model_id in enumerate(model_ids, start=1):
        table.add_row(str(idx), model_id)

    console.print(table)
    rprint(f"\n[bold]{len(model_ids)}[/bold] model(s) available on [dim]{config.base_url}[/dim]")
