"""Auth commands: set-key and check."""
from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.prompt import Prompt

from nvcli.config import load_config, save_config
from nvcli.nvidia_client import NvidiaClient

auth_app = typer.Typer(help="Manage NVIDIA API authentication.")


@auth_app.command("set-key")
def set_key() -> None:
    """Prompt for an NVIDIA API key, validate its format, and save it to config."""
    rprint("[bold cyan]NVIDIA API Key Setup[/bold cyan]")
    rprint("Your key can be found at: [link=https://integrate.api.nvidia.com]https://integrate.api.nvidia.com[/link]")
    rprint()

    api_key = Prompt.ask("[bold]Enter your NVIDIA API key[/bold]", password=True).strip()

    if not api_key:
        rprint("[red]Error: API key cannot be empty.[/red]")
        raise typer.Exit(code=1)

    if not api_key.startswith("nvapi-"):
        rprint(
            "[red]Error: Invalid API key format.[/red] "
            "NVIDIA API keys must start with [bold]nvapi-[/bold]."
        )
        raise typer.Exit(code=1)

    config = load_config()
    config.api_key = api_key
    save_config(config)

    masked = f"nvapi-...{api_key[-4:]}"
    rprint(f"[green]API key saved successfully[/green] ([dim]{masked}[/dim])")
    rprint("Run [bold]nv auth check[/bold] to verify connectivity.")


@auth_app.command("check")
def check() -> None:
    """Verify that the configured API key can authenticate with NVIDIA's API."""
    config = load_config()

    if not config.api_key:
        rprint("[red]  ✗ No API key configured.[/red] Run [bold]nv auth set-key[/bold] first.")
        raise typer.Exit(code=1)

    rprint("[dim]Checking NVIDIA API authentication…[/dim]")

    client = NvidiaClient(config)
    ok = asyncio.run(client.check_auth())

    if ok:
        rprint("[green]  ✓ Authentication successful![/green] Your API key is valid.")
    else:
        rprint(
            "[red]  ✗ Authentication failed.[/red] "
            "Check your API key with [bold]nv auth set-key[/bold]."
        )
        raise typer.Exit(code=1)
