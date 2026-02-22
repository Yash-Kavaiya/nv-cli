"""nv run command — safely execute shell commands with confirmation."""
import asyncio
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console

from nvcli.config import load_config

run_app = typer.Typer()
console = Console()


@run_app.callback(invoke_without_command=True)
def run(
    command: str = typer.Argument(..., help="Shell command to run"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
    fix: bool = typer.Option(False, "--fix", help="If command fails, invoke nv code to fix it"),
    context: str = typer.Option(".", "--context", "-c", help="Working directory for the command"),
):
    """Safely run a shell command with confirmation.

    Shows the command before running, asks for confirmation, then streams output.
    
    With --fix: if the command fails, automatically invokes `nv code` to fix the issue.

    Examples:
        nv run "pytest -q"           # ask before running
        nv run "pytest -q" --force   # skip confirmation  
        nv run "pytest -q" --fix     # run, then fix failures automatically
    """
    asyncio.run(_run_async(command, force, fix, context))


async def _run_async(command: str, force: bool, fix: bool, context: str):
    from nvcli.agent.tools import run_cmd
    
    exit_code, stdout, stderr = await run_cmd(
        command,
        cwd=context,
        skip_confirm=force,
    )
    
    if exit_code == 0 or not fix:
        raise typer.Exit(exit_code)
    
    # Fix loop: command failed and --fix was requested
    rprint(f"\n[bold yellow]Command failed (exit {exit_code}). Starting fix loop...[/bold yellow]")
    
    combined_output = ""
    if stdout:
        combined_output += f"STDOUT:\n{stdout}\n"
    if stderr:
        combined_output += f"STDERR:\n{stderr}\n"
    
    await _fix_loop(command, combined_output, context)


async def _fix_loop(
    original_command: str,
    failure_output: str,
    context: str,
    max_iterations: int = 3,
) -> None:
    """Iterative fix loop: analyze failure -> generate patch -> rerun -> repeat."""
    from nvcli.agent.planner import generate_plan
    from nvcli.agent.executor import execute_plan
    from nvcli.agent.tools import run_cmd
    
    for iteration in range(1, max_iterations + 1):
        rprint(f"\n[bold blue]Fix iteration {iteration}/{max_iterations}[/bold blue]")
        
        # Generate a fix plan based on the failure output
        task = (
            f"Fix the following failure from running `{original_command}`:\n\n"
            f"{failure_output}\n\n"
            f"Analyze the error, find the root cause, and fix it."
        )
        
        try:
            plan = await generate_plan(task, context_path=context)
        except (ValueError, RuntimeError) as e:
            rprint(f"[red]Could not generate fix plan: {e}[/red]")
            return
        
        plan.display()
        
        confirmed = typer.confirm(f"Execute fix plan (iteration {iteration})?", default=True)
        if not confirmed:
            rprint("[dim]Fix loop cancelled.[/dim]")
            return
        
        results = await execute_plan(plan)
        
        # Rerun the original command
        rprint(f"\n[bold]Rerunning: {original_command}[/bold]")
        exit_code, stdout, stderr = await run_cmd(
            original_command, cwd=context, skip_confirm=True
        )
        
        if exit_code == 0:
            rprint(f"\n[bold green]Fixed after {iteration} iteration(s)![/bold green]")
            return
        
        rprint(f"[red]Still failing after iteration {iteration}.[/red]")
        failure_output = ""
        if stdout:
            failure_output += f"STDOUT:\n{stdout}\n"
        if stderr:
            failure_output += f"STDERR:\n{stderr}\n"
    
    rprint(f"[red]Could not fix after {max_iterations} iterations.[/red]")
