"""Stage 1 of the code agent: generates a structured plan from a task description."""
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from rich import print as rprint

from nvcli.config import load_config
from nvcli.nvidia_client import get_client
from nvcli.ui.stream import stream_to_string

console = Console()

PLANNER_SYSTEM_PROMPT = """You are an expert coding agent. Given a task and repository context, create a precise execution plan.

Output ONLY valid JSON in this exact format (no markdown, no explanation):
{
  "summary": "One-sentence description of what this plan accomplishes",
  "steps": [
    {
      "n": 1,
      "description": "What this step does",
      "tool": "read_file",
      "args": {"path": "relative/path.py"}
    },
    {
      "n": 2,
      "description": "What this step does", 
      "tool": "write_file",
      "args": {"path": "relative/path.py", "content_hint": "Add JWT middleware class"}
    },
    {
      "n": 3,
      "description": "Run tests to verify",
      "tool": "run_cmd",
      "args": {"command": "pytest tests/ -q"}
    }
  ]
}

Available tools:
- read_file: {"path": "relative/path"} — Read a file for context
- write_file: {"path": "relative/path", "content_hint": "description of changes"} — Create or modify a file
- search_files: {"pattern": "glob pattern", "path": "."} — Find files matching a pattern
- run_cmd: {"command": "shell command"} — Run a shell command (tests, linting, etc.)

Rules:
- Always start with read_file steps to understand existing code
- Use search_files to find relevant files before reading them
- Be specific about what each step does
- Prefer surgical targeted edits over rewriting entire files
- Include a run_cmd step to verify changes at the end
- Maximum 12 steps"""


@dataclass
class PlanStep:
    n: int
    description: str
    tool: str
    args: dict[str, Any]


@dataclass
class Plan:
    summary: str
    steps: list[PlanStep] = field(default_factory=list)
    raw_context: str = ""

    def display(self) -> None:
        """Display the plan as a rich table."""
        rprint(f"\n[bold blue]Plan:[/bold blue] {self.summary}\n")
        table = Table(
            show_header=True,
            header_style="bold magenta",
            show_lines=True,
            expand=True,
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Tool", style="cyan", width=14)
        table.add_column("Description")
        table.add_column("Args", style="dim", width=30)

        for step in self.steps:
            args_str = ", ".join(f"{k}={v!r}" for k, v in step.args.items())
            if len(args_str) > 50:
                args_str = args_str[:47] + "..."
            table.add_row(str(step.n), step.tool, step.description, args_str)

        console.print(table)


def _collect_repo_context(context_path: str = ".") -> str:
    """Collect repo context: git status + directory tree."""
    parts = []
    root = Path(context_path).resolve()

    # Git status
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=root, timeout=5
        )
        if result.returncode == 0:
            parts.append(f"=== Git Status ===\n{result.stdout.strip() or '(clean)'}")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # File tree (max depth 3, exclude common noise)
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
            capture_output=True, text=True, cwd=root, timeout=5
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    tree_lines = []
    _build_tree(root, tree_lines, prefix="", depth=0, max_depth=3)
    if tree_lines:
        parts.append("=== File Tree ===\n" + "\n".join(tree_lines))

    return "\n\n".join(parts)


def _build_tree(
    path: Path,
    lines: list[str],
    prefix: str,
    depth: int,
    max_depth: int,
) -> None:
    """Recursively build a file tree, skipping hidden and generated dirs."""
    if depth > max_depth:
        return
    skip = {
        ".git", "__pycache__", ".venv", "venv", "node_modules",
        ".mypy_cache", ".pytest_cache", "*.egg-info", "dist", "build",
        ".ruff_cache", ".tox",
    }
    try:
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
    except (PermissionError, OSError):
        return

    for entry in entries:
        if entry.name in skip or entry.name.endswith(".egg-info"):
            continue
        if entry.name.startswith(".") and entry.name not in (".env",):
            continue
        connector = "└── " if entry == entries[-1] else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")
        if entry.is_dir():
            extension = "    " if entry == entries[-1] else "│   "
            _build_tree(entry, lines, prefix + extension, depth + 1, max_depth)


def _parse_plan_json(raw: str) -> Plan:
    """Parse model output (possibly wrapped in markdown) into a Plan."""
    # Strip markdown code fences if present
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Find the JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in model output:\n{raw[:500]}")

    data = json.loads(match.group(0))
    steps = [
        PlanStep(
            n=s["n"],
            description=s["description"],
            tool=s["tool"],
            args=s.get("args", {}),
        )
        for s in data.get("steps", [])
    ]
    return Plan(summary=data.get("summary", "No summary"), steps=steps)


async def generate_plan(
    task: str,
    context_path: str = ".",
    model: str | None = None,
) -> Plan:
    """Generate a structured plan for a coding task.

    Args:
        task: The coding task description.
        context_path: Directory to collect repo context from.
        model: Override model (uses config default if None).

    Returns:
        A Plan with numbered steps.
    """
    config = load_config()
    client = get_client(config)

    rprint("[dim]Collecting repository context...[/dim]")
    context = _collect_repo_context(context_path)

    user_message = f"""Task: {task}

Repository Context:
{context}

Generate a precise execution plan as JSON."""

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    rprint("[dim]Generating plan...[/dim]")
    raw = await stream_to_string(
        client.stream_chat(messages, model=model or config.model, temperature=0.1)
    )

    plan = _parse_plan_json(raw)
    plan.raw_context = context
    return plan
