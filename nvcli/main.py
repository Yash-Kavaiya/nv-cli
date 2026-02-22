"""Main entry point for the nvcli Typer application."""
from __future__ import annotations

from typing import Optional

import typer
from rich import print as rprint

from nvcli import __version__
from nvcli.commands.auth import auth_app
from nvcli.commands.models import models_app
from nvcli.commands.doctor import doctor
from nvcli.commands.chat import chat_app
from nvcli.commands.code import code_app
from nvcli.commands.run import run_app
from nvcli.commands.patch import patch_app
from nvcli.commands.config_cmd import config_app
from nvcli.commands.testgen import testgen_app
from nvcli.commands.logs import logs_app

app = typer.Typer(
    name="nv",
    help=(
        "NVIDIA-powered terminal coding agent.\n\n"
        "Powered by NVIDIA's NIM API (OpenAI-compatible). "
        "Set your key with [bold]nv auth set-key[/bold] to get started."
    ),
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Sub-command groups
app.add_typer(auth_app, name="auth", help="Manage NVIDIA API authentication.")
app.add_typer(models_app, name="models", help="List and inspect available NVIDIA models.")
app.add_typer(chat_app, name="chat", help="Start an interactive chat session.")
app.add_typer(code_app, name="code", help="Run the two-stage code agent on a task.")
app.add_typer(run_app, name="run", help="Safely execute a shell command with confirmation.")
app.add_typer(patch_app, name="patch", help="Preview and apply file patches.")
app.add_typer(config_app, name="config", help="View and manage nvcli configuration.")
app.add_typer(testgen_app, name="testgen", help="Generate AI test cases for a file or function.")
app.add_typer(logs_app, name="logs", help="AI-powered log analysis and root cause analysis.")

# Doctor is a single command, not a group
app.command("doctor")(doctor)


def _version_callback(value: bool) -> None:
    if value:
        rprint(f"[bold cyan]nvcli[/bold cyan] version [bold]{__version__}[/bold]")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show the application version and exit.",
    ),
) -> None:
    """NVIDIA-powered terminal coding agent — like Claude Code, but for NVIDIA's API."""


if __name__ == "__main__":
    app()
