"""Async tool registry for the code agent executor."""
import asyncio
import difflib
import glob as glob_module
from pathlib import Path
from typing import Any

import aiofiles
from rich import print as rprint
from rich.console import Console
from rich.prompt import Confirm

console = Console()

# Registry of pending file mutations (path -> original content)
# Used to generate diffs and allow nv patch preview/apply
_pending_writes: dict[str, tuple[str, str]] = {}  # path -> (original, new)


async def read_file(path: str) -> str:
    """Read a file and return its contents."""
    p = Path(path)
    if not p.exists():
        return f"[File not found: {path}]"
    try:
        async with aiofiles.open(p, "r", encoding="utf-8", errors="replace") as f:
            content = await f.read()
        lines = content.splitlines()
        # Truncate very large files
        if len(lines) > 500:
            return "\n".join(lines[:500]) + f"\n... [truncated, {len(lines) - 500} more lines]"
        return content
    except OSError as e:
        return f"[Error reading {path}: {e}]"


async def write_file(path: str, content: str, skip_confirm: bool = False) -> str:
    """Write content to a file, always showing a diff and asking for confirmation.

    Returns a status string describing what happened.
    """
    from nvcli.ui.diff_view import show_diff  # avoid circular import

    p = Path(path)
    original = ""
    if p.exists():
        try:
            async with aiofiles.open(p, "r", encoding="utf-8", errors="replace") as f:
                original = await f.read()
        except OSError:
            pass

    if original == content:
        return f"No changes needed for {path}"

    show_diff(original, content, path)

    if not skip_confirm:
        confirmed = Confirm.ask(f"\nApply changes to [cyan]{path}[/cyan]?")
        if not confirmed:
            rprint(f"[yellow]Skipped: {path}[/yellow]")
            return f"Skipped: {path}"

    p.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(p, "w", encoding="utf-8") as f:
        await f.write(content)

    # Track for nv patch
    _pending_writes[str(p.resolve())] = (original, content)
    rprint(f"[green]Written: {path}[/green]")
    return f"Written: {path}"


async def search_files(pattern: str, path: str = ".") -> str:
    """Search for files matching a glob pattern."""
    base = Path(path)
    matches = sorted(base.glob(pattern))
    if not matches:
        # Also try recursive
        matches = sorted(base.glob(f"**/{pattern}"))

    if not matches:
        return f"No files found matching '{pattern}' in '{path}'"

    result = f"Found {len(matches)} file(s):\n"
    result += "\n".join(f"  {m.relative_to(base)}" for m in matches[:50])
    if len(matches) > 50:
        result += f"\n  ... and {len(matches) - 50} more"
    return result


def get_pending_diff(file_path: str) -> tuple[str, str] | None:
    """Get pending diff for a file (original, new). Returns None if no pending diff."""
    resolved = str(Path(file_path).resolve())
    return _pending_writes.get(resolved)


def clear_pending(file_path: str | None = None) -> None:
    """Clear pending writes (all or for a specific file)."""
    if file_path is None:
        _pending_writes.clear()
    else:
        _pending_writes.pop(str(Path(file_path).resolve()), None)





async def run_cmd(
    command: str,
    cwd: str = ".",
    capture: bool = True,
    skip_confirm: bool = False,
) -> tuple[int, str, str]:
    """Run a shell command with user confirmation.
    
    Args:
        command: Shell command to run.
        cwd: Working directory.
        capture: Whether to capture output.
        skip_confirm: Skip confirmation prompt.
        
    Returns:
        Tuple of (exit_code, stdout, stderr).
    """
    from nvcli.config import load_config
    config = load_config()
    
    # Check allowlist
    in_allowlist = any(command.startswith(allowed) for allowed in config.command_allowlist)
    
    if not skip_confirm and not in_allowlist:
        rprint(f"\n[bold yellow]Run command:[/bold yellow] [cyan]{command}[/cyan]")
        confirmed = Confirm.ask("Execute?")
        if not confirmed:
            rprint("[yellow]Command skipped.[/yellow]")
            return (0, "", "skipped")
    
    rprint(f"[dim]$ {command}[/dim]")
    
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE if capture else None,
            stderr=asyncio.subprocess.PIPE if capture else None,
            cwd=cwd,
        )
        stdout, stderr = await proc.communicate()
        exit_code = proc.returncode or 0
        
        stdout_str = stdout.decode("utf-8", errors="replace").strip() if stdout else ""
        stderr_str = stderr.decode("utf-8", errors="replace").strip() if stderr else ""
        
        # Display output
        if stdout_str:
            console.print(stdout_str)
        if stderr_str:
            console.print(f"[red]{stderr_str}[/red]")
        
        if exit_code == 0:
            rprint(f"[green]✓ Exited 0[/green]")
        else:
            rprint(f"[red]✗ Exited {exit_code}[/red]")
        
        return (exit_code, stdout_str, stderr_str)
    
    except FileNotFoundError:
        msg = f"Command not found: {command.split()[0]}"
        rprint(f"[red]{msg}[/red]")
        return (127, "", msg)
    except Exception as e:
        rprint(f"[red]Error running command: {e}[/red]")
        return (1, "", str(e))


TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "search_files": search_files,
    "run_cmd": run_cmd,
}
