"""Full-screen TUI for nvcli using textual."""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    Log,
    Static,
)


class ChatLog(Log):
    """Scrollable chat log panel."""

    DEFAULT_CSS = """
    ChatLog {
        border: solid $primary;
        height: 100%;
        padding: 0 1;
    }
    """


class DiffView(Static):
    """Panel for showing diffs."""

    DEFAULT_CSS = """
    DiffView {
        border: solid $warning;
        height: 100%;
        padding: 0 1;
        overflow-y: scroll;
    }
    """

    def update_diff(self, diff_text: str) -> None:
        self.update(diff_text or "[dim]No pending diffs.[/dim]")


class NvCLIApp(App):
    """nvcli full-screen TUI."""

    TITLE = "nvcli — NVIDIA Terminal Agent"
    CSS = """
    #main {
        height: 1fr;
    }
    #file-panel {
        width: 25%;
        border: solid $secondary;
    }
    #chat-panel {
        width: 50%;
        border: solid $primary;
    }
    #diff-panel {
        width: 25%;
        border: solid $warning;
    }
    #input-row {
        height: 3;
        dock: bottom;
    }
    Input {
        width: 100%;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+n", "new_session", "New session"),
    ]

    messages: reactive[list[dict]] = reactive([])

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="file-panel"):
                yield Label("[bold]Files[/bold]", markup=True)
                yield DirectoryTree(".")
            with Vertical(id="chat-panel"):
                yield Label("[bold]Chat[/bold]", markup=True)
                yield ChatLog(id="chat-log")
            with Vertical(id="diff-panel"):
                yield Label("[bold]Diffs[/bold]", markup=True)
                yield DiffView(id="diff-view")
        with Horizontal(id="input-row"):
            yield Input(placeholder="Ask anything... (Ctrl+C to quit)")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chat-log", ChatLog).write_line(
            "Welcome to nvcli TUI! Type a message and press Enter."
        )
        self.query_one(Input).focus()

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return
        event.input.clear()
        self._process_message(user_text)

    @work(thread=False)
    async def _process_message(self, user_text: str) -> None:
        from nvcli.config import load_config
        from nvcli.nvidia_client import get_client
        from nvcli.agent.memory import load_session, save_session

        chat_log = self.query_one("#chat-log", ChatLog)
        chat_log.write_line(f"[bold cyan]You:[/bold cyan] {user_text}")

        config = load_config()
        client = get_client(config)

        if not self.messages:
            self.messages = await load_session()

        self.messages.append({"role": "user", "content": user_text})

        full_response = []
        try:
            async for token in client.stream_chat(self.messages, model=config.model):
                full_response.append(token)
        except RuntimeError as exc:
            chat_log.write_line(f"[bold red]Error:[/bold red] {exc}")
            return

        response_text = "".join(full_response)
        chat_log.write_line(f"[bold green]nvcli:[/bold green] {response_text}")
        self.messages.append({"role": "assistant", "content": response_text})
        await save_session(self.messages)

    def action_new_session(self) -> None:
        self.messages = []
        self.query_one("#chat-log", ChatLog).clear()
        self.query_one("#chat-log", ChatLog).write_line("New session started.")
