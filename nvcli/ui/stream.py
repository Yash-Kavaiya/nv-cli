"""Real-time streaming token display using rich.Live."""
import asyncio
from collections.abc import AsyncIterator
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text

console = Console()

async def stream_to_console(
    token_stream: AsyncIterator[str],
    prefix: str = "",
) -> str:
    """Stream tokens to the console in real-time using rich.Live.
    
    Returns the full accumulated response string.
    """
    accumulated = []
    
    with Live(console=console, refresh_per_second=15, vertical_overflow="visible") as live:
        if prefix:
            live.update(Text(prefix, style="bold cyan"))
        
        async for token in token_stream:
            accumulated.append(token)
            full_text = "".join(accumulated)
            # Try to render as markdown for code blocks, fallback to plain text
            try:
                live.update(Markdown(full_text))
            except Exception:
                live.update(Text(full_text))
    
    return "".join(accumulated)


async def stream_to_string(token_stream: AsyncIterator[str]) -> str:
    """Consume token stream and return full string (no display)."""
    return "".join([token async for token in token_stream])
