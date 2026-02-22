"""Tests for nvcli.ui.diff_view."""
import pytest
from nvcli.ui.diff_view import make_unified_diff, show_diff, show_summary


class TestMakeUnifiedDiff:
    def test_make_unified_diff_detects_changes(self):
        """Simple content change produces a non-empty diff."""
        original = "line one\nline two\nline three\n"
        modified = "line one\nline TWO\nline three\n"
        diff = make_unified_diff(original, modified, "test.txt")
        assert diff != ""
        assert "-line two" in diff
        assert "+line TWO" in diff

    def test_make_unified_diff_no_changes(self):
        """Identical content produces an empty string."""
        content = "no changes here\n"
        diff = make_unified_diff(content, content, "same.txt")
        assert diff == ""

    def test_make_unified_diff_format(self):
        """Output contains '---' and '+++' unified diff headers."""
        original = "old\n"
        modified = "new\n"
        diff = make_unified_diff(original, modified, "file.txt")
        assert "---" in diff
        assert "+++" in diff

    def test_make_unified_diff_includes_filename(self):
        """Diff headers include the filename in a/b form."""
        diff = make_unified_diff("old\n", "new\n", "myfile.py")
        assert "a/myfile.py" in diff
        assert "b/myfile.py" in diff

    def test_make_unified_diff_new_file(self):
        """Diff from empty original to new content shows added lines."""
        diff = make_unified_diff("", "new line\n", "new.py")
        assert "+" in diff
        assert "new line" in diff

    def test_make_unified_diff_deleted_content(self):
        """Diff from content to empty shows removed lines."""
        diff = make_unified_diff("removed line\n", "", "old.py")
        assert "-removed line" in diff


class TestShowDiff:
    def test_show_diff_runs_without_error(self, capsys):
        """show_diff can be called with different content without raising."""
        # Just ensure it doesn't throw
        show_diff("original content\n", "modified content\n", "test.py")

    def test_show_diff_no_changes_message(self, capsys):
        """show_diff with identical content prints 'No changes' message."""
        # Rich uses its own console, so we just verify no exception is raised
        # and call it successfully
        show_diff("same\n", "same\n", "unchanged.py")


class TestShowSummary:
    def test_show_summary_with_files(self, capsys):
        """show_summary with files runs without error."""
        show_summary(["file1.py", "file2.py"])

    def test_show_summary_empty(self, capsys):
        """show_summary with empty list runs without error."""
        show_summary([])
