"""Session memory: load/save chat history to ~/.nvcli/sessions/."""
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Any

import aiofiles

from nvcli.config import load_config


def _get_session_path(name: str = "last") -> Path:
    config = load_config()
    sessions_dir = Path(config.session_dir).expanduser()
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir / f"{name}.json"


async def load_session(name: str = "last") -> list[dict[str, Any]]:
    """Load session messages from disk. Returns empty list if not found."""
    path = _get_session_path(name)
    if not path.exists():
        return []
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
        if isinstance(data, list):
            return data
        return data.get("messages", [])
    except (json.JSONDecodeError, OSError):
        return []


async def save_session(
    messages: list[dict[str, Any]],
    name: str = "last",
) -> None:
    """Save session messages to disk."""
    path = _get_session_path(name)
    data = {
        "name": name,
        "saved_at": datetime.now().isoformat(),
        "message_count": len(messages),
        "messages": messages,
    }
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=2, ensure_ascii=False))


async def list_sessions() -> list[str]:
    """List all saved session names."""
    config = load_config()
    sessions_dir = Path(config.session_dir).expanduser()
    if not sessions_dir.exists():
        return []
    return [p.stem for p in sorted(sessions_dir.glob("*.json"))]


def clear_session(name: str = "last") -> None:
    """Delete a session file."""
    path = _get_session_path(name)
    if path.exists():
        path.unlink()
