"""nv testgen — AI test-case generator."""
import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

testgen_app = typer.Typer()


@testgen_app.callback(invoke_without_command=True)
def testgen(
    target: str = typer.Argument(..., help="Target to generate tests for (e.g. utils.py or utils.py:my_function)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output test file path"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override model"),
    framework: str = typer.Option("pytest", "--framework", "-f", help="Test framework (pytest, unittest)"),
):
    """Generate pytest test cases for a function or module using AI.

    Examples:
        nv testgen utils.py
        nv testgen utils.py:parse_date
        nv testgen app.py:MyClass --output tests/test_myclass.py
    """
    asyncio.run(_testgen_async(target, output, model, framework))


async def _testgen_async(
    target: str,
    output: Optional[str],
    model: Optional[str],
    framework: str,
) -> None:
    from nvcli.config import load_config
    from nvcli.nvidia_client import get_client
    from nvcli.ui.stream import stream_to_string
    import aiofiles

    config = load_config()
    client = get_client(config)

    # Parse target: file[:function_or_class]
    parts = target.split(":", 1)
    file_path = parts[0]
    symbol = parts[1] if len(parts) > 1 else None

    # Read source file
    source_path = Path(file_path)
    if not source_path.exists():
        rprint(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)

    async with aiofiles.open(source_path, "r", encoding="utf-8") as f:
        source_code = await f.read()

    # Build prompt
    focus = f"the `{symbol}` function/class" if symbol else "all public functions and classes"
    prompt = f"""Generate comprehensive {framework} tests for {focus} in the following Python code.

Source file: {file_path}

```python
{source_code}
```

Requirements:
- Use {framework} conventions
- Cover happy path, edge cases, and error cases
- Use descriptive test names (test_<function>_<scenario>)
- Add docstrings to test classes
- Mock external dependencies
- Return ONLY the test code, no explanation
"""

    messages = [
        {
            "role": "system",
            "content": "You are an expert Python test engineer. Generate comprehensive, working tests.",
        },
        {"role": "user", "content": prompt},
    ]

    rprint(f"[bold blue]Generating tests for:[/bold blue] {target}")

    test_code = await stream_to_string(
        client.stream_chat(messages, model=model or config.model, temperature=0.1)
    )

    # Strip markdown fences if present
    import re
    test_code = re.sub(r"^```(?:python)?\s*", "", test_code.strip(), flags=re.MULTILINE)
    test_code = re.sub(r"\s*```\s*$", "", test_code.strip(), flags=re.MULTILINE)

    # Determine output path
    if output:
        out_path = Path(output)
    else:
        stem = source_path.stem
        func_part = f"_{symbol}" if symbol else ""
        out_path = source_path.parent / f"test_{stem}{func_part}.py"

    async with aiofiles.open(out_path, "w", encoding="utf-8") as f:
        await f.write(test_code.strip() + "\n")

    rprint(f"[green]Tests written to: {out_path}[/green]")
    rprint(f"[dim]Run with: pytest {out_path} -v[/dim]")
