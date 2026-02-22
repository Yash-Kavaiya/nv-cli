"""nv logs — AI-powered log analysis and root cause analysis."""
import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

logs_app = typer.Typer()


@logs_app.callback(invoke_without_command=True)
def logs(
    ctx: typer.Context,
):
    """AI-powered log analysis commands."""


@logs_app.command("analyze")
def analyze(
    log_file: Optional[str] = typer.Argument(None, help="Log file to analyze (reads stdin if omitted)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override model"),
    tail: int = typer.Option(200, "--tail", "-n", help="Number of lines to analyze (from end)"),
):
    """Perform AI root-cause analysis on a log file or stdin.

    Examples:
        nv logs analyze app.log
        cat app.log | nv logs analyze
        nv logs analyze app.log --tail 500
        journalctl -u myservice | nv logs analyze
    """
    asyncio.run(_analyze_async(log_file, model, tail))


async def _analyze_async(
    log_file: Optional[str],
    model: Optional[str],
    tail: int,
) -> None:
    from nvcli.config import load_config
    from nvcli.nvidia_client import get_client
    from nvcli.ui.stream import stream_to_console

    config = load_config()
    client = get_client(config)

    # Read log content
    if log_file:
        path = Path(log_file)
        if not path.exists():
            rprint(f"[red]Log file not found: {log_file}[/red]")
            raise typer.Exit(1)
        content = path.read_text(encoding="utf-8", errors="replace")
        source = log_file
    else:
        content = sys.stdin.read()
        source = "stdin"

    # Take last N lines
    lines = content.splitlines()
    if len(lines) > tail:
        lines = lines[-tail:]
        rprint(f"[dim]Analyzing last {tail} of {len(content.splitlines())} lines from {source}[/dim]")
    else:
        rprint(f"[dim]Analyzing {len(lines)} lines from {source}[/dim]")

    log_excerpt = "\n".join(lines)

    prompt = f"""Analyze these logs and provide a concise root cause analysis (RCA).

Log content:
```
{log_excerpt}
```

Provide:
1. **Error Summary**: What went wrong (1-2 sentences)
2. **Root Cause**: The most likely underlying cause
3. **Affected Components**: Which services/functions are involved
4. **Recommended Fix**: Specific actionable steps to resolve it
5. **Prevention**: How to prevent this in the future

Be concise and actionable. Focus on the most critical error."""

    messages = [
        {
            "role": "system",
            "content": "You are an expert SRE and systems engineer. Provide precise, actionable root cause analysis.",
        },
        {"role": "user", "content": prompt},
    ]

    rprint(f"\n[bold blue]Root Cause Analysis[/bold blue] — {source}\n")
    await stream_to_console(client.stream_chat(messages, model=model or config.model))
