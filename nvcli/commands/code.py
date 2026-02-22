"""nv code command — two-stage plan+execute code agent."""
import asyncio
from typing import Optional

import typer
from rich import print as rprint

from nvcli.agent.planner import generate_plan

code_app = typer.Typer()


@code_app.callback(invoke_without_command=True)
def code(
    task: str = typer.Argument(..., help="Coding task to perform"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show plan only, don't execute"),
    context: str = typer.Option(".", "--context", "-c", help="Directory context for repo analysis"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override model"),
):
    """Run the two-stage code agent on a coding task.

    Stage 1: Generates a numbered execution plan.
    Stage 2: Executes each step with user confirmation (skipped with --dry-run).

    Example:
        nv code "add JWT middleware to app.py"
        nv code "add docstrings to utils.py" --dry-run
    """
    asyncio.run(_code_async(task, dry_run, context, model))


async def _code_async(task: str, dry_run: bool, context: str, model: Optional[str]):
    rprint(f"\n[bold blue]Task:[/bold blue] {task}")
    if dry_run:
        rprint("[yellow]Dry-run mode: plan only, no execution.[/yellow]")

    # Stage 1: Generate plan
    try:
        plan = await generate_plan(task, context_path=context, model=model)
    except ValueError as e:
        rprint(f"[red]Failed to generate plan: {e}[/red]")
        raise typer.Exit(1)
    except RuntimeError as e:
        rprint(f"[red]API error: {e}[/red]")
        raise typer.Exit(1)

    plan.display()

    if dry_run:
        rprint("\n[dim]Dry-run complete. Use without --dry-run to execute.[/dim]")
        return

    # Ask user to confirm before executing
    rprint()
    confirmed = typer.confirm("Execute this plan?", default=True)
    if not confirmed:
        rprint("[dim]Plan cancelled.[/dim]")
        return

    # Stage 2: Execute
    from nvcli.agent.executor import execute_plan
    results = await execute_plan(plan)

    executed = sum(1 for r in results if not r.skipped and not r.aborted)
    skipped = sum(1 for r in results if r.skipped)
    rprint(f"\n[bold green]Done![/bold green] {executed} step(s) executed, {skipped} skipped.")
