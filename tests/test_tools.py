"""Tests for nvcli.agent.tools."""
import asyncio
from pathlib import Path

import pytest

import nvcli.agent.tools as tools_module
from nvcli.agent.tools import (
    read_file,
    write_file,
    search_files,
    get_pending_diff,
    clear_pending,
)


@pytest.fixture(autouse=True)
def clear_pending_writes():
    """Clear pending writes before and after each test."""
    tools_module._pending_writes.clear()
    yield
    tools_module._pending_writes.clear()


class TestReadFile:
    @pytest.mark.asyncio
    async def test_read_file_existing(self, tmp_path):
        """Creates a temp file and reads it successfully."""
        f = tmp_path / "hello.txt"
        f.write_text("Hello, world!")
        result = await read_file(str(f))
        assert result == "Hello, world!"

    @pytest.mark.asyncio
    async def test_read_file_nonexistent(self, tmp_path):
        """Returns '[File not found: ...]' string — does not raise."""
        missing = str(tmp_path / "does_not_exist.txt")
        result = await read_file(missing)
        assert result.startswith("[File not found:")
        assert missing in result

    @pytest.mark.asyncio
    async def test_read_file_truncates_large_file(self, tmp_path):
        """A file with 600 lines gets truncated to 500 lines."""
        f = tmp_path / "big.txt"
        lines = [f"line {i}" for i in range(600)]
        f.write_text("\n".join(lines))
        result = await read_file(str(f))
        result_lines = result.splitlines()
        # First 500 lines of content plus truncation notice
        assert "truncated" in result
        assert "100 more lines" in result
        # The content lines (excluding the truncation line) should be 500
        content_lines = [ln for ln in result_lines if not ln.startswith("...")]
        assert len(content_lines) == 500


class TestWriteFile:
    @pytest.mark.asyncio
    async def test_write_file_skip_confirm(self, tmp_path):
        """write_file with skip_confirm=True writes without prompting."""
        f = tmp_path / "output.txt"
        result = await write_file(str(f), "new content", skip_confirm=True)
        assert result == f"Written: {f}"
        assert f.read_text(encoding="utf-8") == "new content"

    @pytest.mark.asyncio
    async def test_write_file_no_changes_needed(self, tmp_path):
        """Returns 'No changes needed' when content is identical."""
        f = tmp_path / "same.txt"
        f.write_text("existing content")
        result = await write_file(str(f), "existing content", skip_confirm=True)
        assert "No changes needed" in result

    @pytest.mark.asyncio
    async def test_write_file_creates_parent_dirs(self, tmp_path):
        """Creates parent directories automatically."""
        f = tmp_path / "subdir" / "nested" / "file.txt"
        result = await write_file(str(f), "nested content", skip_confirm=True)
        assert result == f"Written: {f}"
        assert f.exists()
        assert f.read_text(encoding="utf-8") == "nested content"


class TestSearchFiles:
    @pytest.mark.asyncio
    async def test_search_files_finds_pattern(self, tmp_path):
        """Creates files and searches by glob pattern."""
        (tmp_path / "foo.py").write_text("# foo")
        (tmp_path / "bar.py").write_text("# bar")
        (tmp_path / "README.md").write_text("# readme")
        result = await search_files("*.py", str(tmp_path))
        assert "Found 2 file(s)" in result
        assert "foo.py" in result
        assert "bar.py" in result

    @pytest.mark.asyncio
    async def test_search_files_no_match(self, tmp_path):
        """Returns 'No files found' message when nothing matches."""
        result = await search_files("*.nonexistent", str(tmp_path))
        assert "No files found" in result

    @pytest.mark.asyncio
    async def test_search_files_recursive(self, tmp_path):
        """Finds files in subdirectories via fallback recursive glob."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "deep.txt").write_text("deep")
        result = await search_files("deep.txt", str(tmp_path))
        assert "Found" in result
        assert "deep.txt" in result


class TestGetPendingDiff:
    @pytest.mark.asyncio
    async def test_get_pending_diff_after_write(self, tmp_path):
        """After writing a file, get_pending_diff returns (original, new)."""
        f = tmp_path / "tracked.txt"
        f.write_text("original content")
        await write_file(str(f), "new content", skip_confirm=True)
        result = get_pending_diff(str(f))
        assert result is not None
        original, new = result
        assert original == "original content"
        assert new == "new content"

    @pytest.mark.asyncio
    async def test_get_pending_diff_no_entry(self, tmp_path):
        """Returns None when no pending diff exists for a file."""
        f = tmp_path / "untracked.txt"
        result = get_pending_diff(str(f))
        assert result is None

    def test_clear_pending_specific_file(self, tmp_path):
        """clear_pending removes only the specified file's entry."""
        path_a = str((tmp_path / "a.txt").resolve())
        path_b = str((tmp_path / "b.txt").resolve())
        tools_module._pending_writes[path_a] = ("orig_a", "new_a")
        tools_module._pending_writes[path_b] = ("orig_b", "new_b")
        clear_pending(path_a)
        assert get_pending_diff(path_a) is None
        assert tools_module._pending_writes.get(path_b) == ("orig_b", "new_b")

    def test_clear_pending_all(self, tmp_path):
        """clear_pending() with no argument clears everything."""
        path_a = str((tmp_path / "a.txt").resolve())
        tools_module._pending_writes[path_a] = ("orig", "new")
        clear_pending()
        assert len(tools_module._pending_writes) == 0
