"""Colored unified diff display using rich."""
import difflib
from rich.console import Console
from rich.syntax import Syntax
from rich import print as rprint
from rich.panel import Panel

console = Console()


def make_unified_diff(original: str, modified: str, filename: str = "file") -> str:
    """Generate a unified diff string."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
    )
    return "".join(diff)


def show_diff(original: str, modified: str, filename: str = "file") -> None:
    """Display a colored unified diff in the terminal."""
    diff_text = make_unified_diff(original, modified, filename)

    if not diff_text:
        rprint(f"[dim]No changes in {filename}[/dim]")
        return

    syntax = Syntax(
        diff_text,
        "diff",
        theme="monokai",
        line_numbers=False,
        word_wrap=False,
    )
    console.print(Panel(syntax, title=f"[bold]Changes: {filename}[/bold]", border_style="yellow"))


def show_summary(changed_files: list[str]) -> None:
    """Show a summary of all changed files."""
    if not changed_files:
        rprint("[dim]No files changed.[/dim]")
        return
    rprint(f"\n[bold green]Changed {len(changed_files)} file(s):[/bold green]")
    for f in changed_files:
        rprint(f"  [cyan]{f}[/cyan]")
