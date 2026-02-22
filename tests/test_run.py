"""Tests for nv run command and run_cmd tool."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nvcli.agent.tools import run_cmd


class TestRunCmdSuccess:
    @pytest.mark.asyncio
    async def test_run_cmd_success(self):
        """Mock subprocess returning exit code 0 with stdout."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"hello world", b""))

        with patch("asyncio.create_subprocess_shell", return_value=mock_proc) as mock_create:
            exit_code, stdout, stderr = await run_cmd(
                "echo hello world", skip_confirm=True
            )

        assert exit_code == 0
        assert stdout == "hello world"
        assert stderr == ""
        mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_cmd_failure_returns_nonzero_exit(self):
        """Exit code is passed through from subprocess."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"some error"))

        with patch("asyncio.create_subprocess_shell", return_value=mock_proc):
            exit_code, stdout, stderr = await run_cmd(
                "false", skip_confirm=True
            )

        assert exit_code == 1
        assert stdout == ""
        assert stderr == "some error"

    @pytest.mark.asyncio
    async def test_run_cmd_not_found(self):
        """Command not found raises FileNotFoundError, returns 127."""
        with patch(
            "asyncio.create_subprocess_shell",
            side_effect=FileNotFoundError("No such file or directory"),
        ):
            exit_code, stdout, stderr = await run_cmd(
                "nonexistent_command_xyz", skip_confirm=True
            )

        assert exit_code == 127
        assert stdout == ""
        assert "Command not found" in stderr

    @pytest.mark.asyncio
    async def test_run_cmd_skip_confirm_bypasses_prompt(self):
        """With skip_confirm=True, no confirmation prompt is shown."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))

        with patch("asyncio.create_subprocess_shell", return_value=mock_proc):
            with patch("nvcli.agent.tools.Confirm.ask") as mock_confirm:
                exit_code, stdout, stderr = await run_cmd(
                    "echo ok", skip_confirm=True
                )

        mock_confirm.assert_not_called()
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_run_cmd_in_allowlist_bypasses_prompt(self):
        """A command that starts with an allowlisted prefix skips confirmation."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"tests passed", b""))

        mock_config = MagicMock()
        mock_config.command_allowlist = ["pytest"]

        with patch("nvcli.agent.tools.Confirm.ask") as mock_confirm:
            with patch("nvcli.config.load_config", return_value=mock_config):
                with patch("asyncio.create_subprocess_shell", return_value=mock_proc):
                    exit_code, stdout, stderr = await run_cmd(
                        "pytest -q", skip_confirm=False
                    )

        mock_confirm.assert_not_called()
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_run_cmd_captures_stdout_and_stderr(self):
        """Both stdout and stderr are captured and returned correctly."""
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(
            return_value=(b"output line\n", b"warning line\n")
        )

        with patch("asyncio.create_subprocess_shell", return_value=mock_proc):
            exit_code, stdout, stderr = await run_cmd(
                "some command", skip_confirm=True
            )

        assert exit_code == 0
        assert stdout == "output line"
        assert stderr == "warning line"

    @pytest.mark.asyncio
    async def test_run_cmd_exception_returns_exit_1(self):
        """An unexpected exception during subprocess creation returns exit code 1."""
        with patch(
            "asyncio.create_subprocess_shell",
            side_effect=OSError("something went wrong"),
        ):
            exit_code, stdout, stderr = await run_cmd(
                "some command", skip_confirm=True
            )

        assert exit_code == 1
        assert "something went wrong" in stderr
