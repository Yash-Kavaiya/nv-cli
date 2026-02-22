"""Chat REPL with streaming, session persistence, and slash commands."""
from __future__ import annotations

import asyncio
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from pathlib import Path

from nvcli.config import load_config
from nvcli.nvidia_client import get_client
from nvcli.agent.memory import load_session, save_session, list_sessions
from nvcli.ui.stream import stream_to_console

chat_app = typer.Typer()
console = Console()

SYSTEM_PROMPT = "You are a helpful coding assistant with access to the user's codebase. Be concise and precise."


@chat_app.callback(invoke_without_command=True)
def chat(
    tui: bool = typer.Option(False, "--tui", help="Launch full TUI mode"),
    new: bool = typer.Option(False, "--new", help="Start fresh session"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override model"),
):
    """Start an interactive chat session with streaming output."""
    asyncio.run(_chat_async(tui, new, model))


async def _chat_async(tui: bool, new: bool, model: Optional[str]):
    if tui:
        from nvcli.ui.tui import NvCLIApp
        await NvCLIApp().run_async()
        return

    config = load_config()
    active_model = model or config.model
    client = get_client(config)

    # Load or create session
    messages = [] if new else await load_session()
    messages_with_system = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    # Setup prompt_toolkit session
    history_path = Path.home() / ".nvcli" / ".history"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    session = PromptSession(
        history=FileHistory(str(history_path)),
        style=Style.from_dict({"prompt": "cyan bold"}),
    )

    rprint(f"[bold blue]nvcli chat[/bold blue] — model: [cyan]{active_model}[/cyan]")
    if messages:
        rprint(f"[dim]Restored {len(messages)} messages from last session. /new to clear.[/dim]")
    rprint("[dim]Type /help for commands, Ctrl+C or /exit to quit.[/dim]\n")

    try:
        while True:
            try:
                user_input = await session.prompt_async("> ")
            except EOFError:
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                result = await _handle_slash(user_input, messages, active_model, client, config)
                if result == "EXIT":
                    break
                elif result is not None:
                    active_model = result  # /model returns new model name
                continue

            # Normal chat message
            messages.append({"role": "user", "content": user_input})
            messages_with_system = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

            rprint()  # blank line before response
            response = await stream_to_console(
                client.stream_chat(messages_with_system, model=active_model)
            )
            rprint()  # blank line after response

            messages.append({"role": "assistant", "content": response})
            await save_session(messages)

    except KeyboardInterrupt:
        pass
    finally:
        await save_session(messages)
        rprint("\n[dim]Session saved. Goodbye![/dim]")


async def _handle_slash(
    cmd: str,
    messages: list,
    active_model: str,
    client,
    config,
) -> Optional[str]:
    """Handle slash commands. Returns new model name for /model, 'EXIT' to quit, None otherwise."""
    parts = cmd.strip().split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else None

    if command in ("/exit", "/quit"):
        return "EXIT"

    elif command == "/clear" or command == "/new":
        messages.clear()
        rprint("[dim]Session cleared.[/dim]")

    elif command == "/help":
        table = Table(title="Slash Commands", show_header=True, header_style="bold magenta")
        table.add_column("Command", style="cyan")
        table.add_column("Description")
        cmds = [
            ("/model", "Show/switch model"),
            ("/clear", "Clear chat history"),
            ("/new", "Start fresh session"),
            ("/save [name]", "Save session with optional name"),
            ("/load [name]", "Load a saved session"),
            ("/sessions", "List all saved sessions"),
            ("/exit", "Save and quit"),
            ("/help", "Show this help"),
        ]
        for c, d in cmds:
            table.add_row(c, d)
        console.print(table)

    elif command == "/model":
        # List models and allow switching
        rprint(f"[dim]Current model: [cyan]{active_model}[/cyan][/dim]")
        try:
            models = await client.list_models()
            table = Table(show_header=True, header_style="bold")
            table.add_column("#", style="dim", width=4)
            table.add_column("Model ID", style="cyan")
            for i, m in enumerate(models, 1):
                marker = " ◀" if m == active_model else ""
                table.add_row(str(i), m + marker)
            console.print(table)

            choice = input("Switch to # (or Enter to keep current): ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(models):
                    new_model = models[idx]
                    rprint(f"[green]Switched to: {new_model}[/green]")
                    return new_model  # Signal model change
        except Exception as e:
            rprint(f"[red]Could not fetch models: {e}[/red]")

    elif command == "/save":
        name = arg or "last"
        await save_session(messages, name)
        rprint(f"[green]Session saved as: {name}[/green]")

    elif command == "/load":
        if arg:
            loaded = await load_session(arg)
            messages.clear()
            messages.extend(loaded)
            rprint(f"[green]Loaded session '{arg}': {len(loaded)} messages[/green]")
        else:
            sessions = await list_sessions()
            if not sessions:
                rprint("[dim]No saved sessions.[/dim]")
            else:
                for i, s in enumerate(sessions, 1):
                    rprint(f"  {i}. {s}")
                rprint("[dim]Use /load <name> to load a session.[/dim]")

    elif command == "/sessions":
        sessions = await list_sessions()
        if not sessions:
            rprint("[dim]No saved sessions.[/dim]")
        else:
            for s in sessions:
                rprint(f"  • {s}")

    else:
        rprint(f"[red]Unknown command: {command}. Type /help for available commands.[/red]")

    return None
