"""Stage 2 of the code agent: execute plan steps with user confirmation at each step."""
from dataclasses import dataclass, field
from typing import Any

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from nvcli.agent.planner import Plan, PlanStep
from nvcli.agent.tools import read_file, write_file, search_files, run_cmd, TOOL_MAP
from nvcli.ui.diff_view import show_summary

console = Console()


@dataclass
class ExecutionResult:
    step: PlanStep
    output: str
    skipped: bool = False
    aborted: bool = False


async def execute_plan(plan: Plan, dry_run: bool = False) -> list[ExecutionResult]:
    """Execute a plan step by step with user confirmation at each step.

    Args:
        plan: The Plan to execute.
        dry_run: If True, show what would happen but don't execute.

    Returns:
        List of ExecutionResult for each step.
    """
    results: list[ExecutionResult] = []
    total = len(plan.steps)
    changed_files: list[str] = []

    rprint(f"\n[bold]Executing {total} step(s)...[/bold]")
    rprint("[dim]At each step: y=continue, n=skip, a=abort[/dim]\n")

    for step in plan.steps:
        rprint(Panel(
            f"[bold cyan]{step.tool}[/bold cyan]  {step.description}\n"
            f"[dim]args: {step.args}[/dim]",
            title=f"[bold]Step {step.n}/{total}[/bold]",
            border_style="blue",
        ))

        if dry_run:
            rprint("[dim](dry-run: skipping)[/dim]")
            results.append(ExecutionResult(step=step, output="dry-run", skipped=True))
            continue

        # Prompt user
        choice = Prompt.ask(
            f"[bold]Step {step.n}/{total}[/bold]",
            choices=["y", "n", "a"],
            default="y",
        )

        if choice == "a":
            rprint("[red]Aborted by user.[/red]")
            results.append(ExecutionResult(step=step, output="aborted", aborted=True))
            break

        if choice == "n":
            rprint(f"[yellow]Skipped step {step.n}.[/yellow]")
            results.append(ExecutionResult(step=step, output="skipped", skipped=True))
            continue

        # Execute the tool
        output = await _execute_tool(step)
        results.append(ExecutionResult(step=step, output=output))

        # Track changed files
        if step.tool == "write_file" and "Written:" in output:
            changed_files.append(step.args.get("path", "unknown"))

        rprint(f"[dim]→ {output[:200]}[/dim]\n")

    show_summary(changed_files)
    return results


async def _execute_tool(step: PlanStep) -> str:
    """Execute a single plan step's tool call."""
    tool_fn = TOOL_MAP.get(step.tool)

    if tool_fn is None:
        return f"Unknown tool: {step.tool}"

    try:
        if step.tool == "read_file":
            return await read_file(step.args.get("path", ""))
        elif step.tool == "write_file":
            # For write_file from planner, we need to generate the content
            # The planner provides content_hint, not actual content
            # So we read the file first, then ask the model to produce full content
            # For Task 4, we'll use content_hint as a placeholder content marker
            content_hint = step.args.get("content_hint", "")
            path = step.args.get("path", "")
            content = step.args.get("content", content_hint)
            if not content or content == content_hint:
                # Mark as needing content generation (will be enhanced in Task 5 with full agent loop)
                return f"Skipped write_file({path}): content generation requires model call (Task 5)"
            return await write_file(path, content)
        elif step.tool == "search_files":
            return await search_files(
                step.args.get("pattern", "*"),
                step.args.get("path", "."),
            )
        elif step.tool == 'run_cmd':
            command = step.args.get('command', '')
            exit_code, stdout, stderr = await run_cmd(command, skip_confirm=False)
            return 'exit_code=' + str(exit_code) + chr(10) + 'stdout=' + stdout[:500] + chr(10) + 'stderr=' + stderr[:200]
        else:
            return f"Tool '{step.tool}' not yet implemented"
    except Exception as e:
        return f"Error in {step.tool}: {e}"
