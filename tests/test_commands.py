"""CLI command smoke tests using typer.testing.CliRunner."""
import pytest
from typer.testing import CliRunner
from nvcli.main import app

runner = CliRunner()


def test_version_flag():
    """--version prints the version string and exits 0."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help_shows_all_commands():
    """--help lists every registered sub-command."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ["auth", "models", "doctor", "chat", "code", "run", "patch", "config", "testgen", "logs"]:
        assert cmd in result.output, f"Command '{cmd}' not found in help output"


def test_config_show():
    """config show prints config without crashing."""
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0


def test_doctor_without_key_exits_1():
    """doctor exits with code 1 when NVIDIA_API_KEY is absent."""
    import os
    env = {k: v for k, v in os.environ.items() if k != "NVIDIA_API_KEY"}
    result = runner.invoke(app, ["doctor"], env=env)
    assert result.exit_code == 1


def test_models_list_without_key_shows_error():
    """models list shows an error or exits non-zero without an API key."""
    import os
    env = {k: v for k, v in os.environ.items() if k != "NVIDIA_API_KEY"}
    result = runner.invoke(app, ["models", "list"], env=env)
    # Should either print 'key' in output or exit non-zero
    assert "key" in result.output.lower() or result.exit_code != 0


def test_testgen_help():
    """testgen --help shows usage without error."""
    result = runner.invoke(app, ["testgen", "--help"])
    assert result.exit_code == 0
    assert "target" in result.output.lower() or "testgen" in result.output.lower()


def test_logs_help():
    """logs --help shows usage without error."""
    result = runner.invoke(app, ["logs", "--help"])
    assert result.exit_code == 0


def test_logs_analyze_help():
    """logs analyze --help shows usage without error."""
    result = runner.invoke(app, ["logs", "analyze", "--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output.lower() or "log" in result.output.lower()


def test_testgen_missing_file(tmp_path):
    """testgen exits non-zero when the source file does not exist."""
    result = runner.invoke(app, ["testgen", str(tmp_path / "nonexistent.py")])
    # Should exit with error code or print 'not found'
    assert result.exit_code != 0 or "not found" in result.output.lower()


def test_chat_help():
    """chat --help lists --tui option."""
    result = runner.invoke(app, ["chat", "--help"])
    assert result.exit_code == 0
    assert "--tui" in result.output
