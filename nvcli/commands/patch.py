"""nv patch commands — preview and apply pending file changes."""
import typer
from rich import print as rprint
from nvcli.agent.tools import get_pending_diff
from nvcli.ui.diff_view import show_diff

patch_app = typer.Typer()


@patch_app.command("preview")
def preview(file: str = typer.Argument(..., help="File to preview patch for")):
    """Preview pending patch for a file."""
    result = get_pending_diff(file)
    if result is None:
        rprint(f"[yellow]No pending patch for: {file}[/yellow]")
        return
    original, new = result
    show_diff(original, new, file)


@patch_app.command("apply")
def apply(file: str = typer.Argument(..., help="File to apply patch to")):
    """Apply pending patch to a file (with confirmation)."""
    import asyncio
    from nvcli.agent.tools import write_file, clear_pending
    result = get_pending_diff(file)
    if result is None:
        rprint(f"[yellow]No pending patch for: {file}[/yellow]")
        return
    original, new = result
    show_diff(original, new, file)
    confirmed = typer.confirm(f"Apply changes to {file}?")
    if confirmed:
        asyncio.run(write_file(file, new, skip_confirm=True))
        clear_pending(file)
        rprint(f"[green]Applied patch to {file}[/green]")
