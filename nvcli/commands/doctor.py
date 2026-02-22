"""Doctor command — run environment health checks."""
from __future__ import annotations

import asyncio
import sys

import typer
from rich.console import Console
from rich.panel import Panel

from nvcli.config import load_config, get_config_path
from nvcli.nvidia_client import NvidiaClient


def _get_console() -> Console:
    """Return a Console that works on both Windows and POSIX."""
    return Console()


def _ok(con: Console, label: str) -> None:
    con.print(f"  [green]OK[/green]  {label}")


def _fail(con: Console, label: str, reason: str) -> None:
    con.print(f"  [red]FAIL[/red] {label}[dim]: {reason}[/dim]")


def doctor() -> None:
    """Run a series of environment health checks for nvcli."""
    con = _get_console()
    con.print(Panel("[bold]nvcli doctor[/bold]", border_style="blue", expand=False))
    con.print()

    failed = False

    # Check 1: Python version
    major, minor = sys.version_info.major, sys.version_info.minor
    if (major, minor) >= (3, 11):
        _ok(con, f"Python version ({major}.{minor}) >= 3.11")
    else:
        _fail(con, f"Python version ({major}.{minor})", "requires Python >= 3.11")
        failed = True

    # Check 2: Config file exists
    config_path = get_config_path()
    if config_path.exists():
        _ok(con, f"Config file found ({config_path})")
    else:
        _fail(
            con,
            "Config file",
            f"not found at {config_path}  -- run 'nv auth set-key' to create it",
        )
        failed = True

    # Check 3 & 4: API key configured and valid format
    config = load_config()
    if config.api_key:
        _ok(con, "API key is configured")
        if config.api_key.startswith("nvapi-"):
            _ok(con, "API key format looks valid (starts with 'nvapi-')")
        else:
            _fail(con, "API key format", "key does not start with 'nvapi-'")
            failed = True
    else:
        _fail(con, "API key configured", "no API key found -- run 'nv auth set-key'")
        failed = True
        _fail(con, "API key format", "cannot check format -- no key configured")

    # Check 5: Connectivity
    if config.api_key:
        con.print("  [dim]Testing connectivity to NVIDIA API...[/dim]")
        client = NvidiaClient(config)
        try:
            models = asyncio.run(client.list_models())
            if models:
                _ok(con, f"NVIDIA API reachable ({len(models)} model(s) available)")
            else:
                _fail(con, "NVIDIA API reachable", "connected but no models returned")
                failed = True
        except Exception as exc:
            _fail(con, "NVIDIA API reachable", str(exc))
            failed = True
    else:
        _fail(con, "NVIDIA API connectivity", "skipped -- no API key configured")
        failed = True

    con.print()
    if failed:
        con.print("[red bold]Some checks failed.[/red bold] See above for details.")
        raise typer.Exit(code=1)
    else:
        con.print(
            "[green bold]All checks passed![/green bold] nvcli is ready to use."
        )
