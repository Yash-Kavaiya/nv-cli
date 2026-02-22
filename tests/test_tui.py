"""Smoke tests for the TUI module."""
import pytest


def test_tui_module_imports():
    """Ensure TUI module imports without errors."""
    from nvcli.ui.tui import NvCLIApp
    assert NvCLIApp is not None


def test_tui_app_is_textual_app():
    """Ensure NvCLIApp is a proper textual App."""
    from textual.app import App
    from nvcli.ui.tui import NvCLIApp
    assert issubclass(NvCLIApp, App)


def test_tui_has_correct_title():
    """Ensure TUI title includes 'nvcli'."""
    from nvcli.ui.tui import NvCLIApp
    app = NvCLIApp()
    assert "nvcli" in app.TITLE.lower()


def test_tui_chat_log_widget_exists():
    """Ensure ChatLog widget is defined and is a Log subclass."""
    from textual.widgets import Log
    from nvcli.ui.tui import ChatLog
    assert issubclass(ChatLog, Log)


def test_tui_diff_view_widget_exists():
    """Ensure DiffView widget is defined and has update_diff method."""
    from nvcli.ui.tui import DiffView
    assert hasattr(DiffView, "update_diff")


def test_tui_has_bindings():
    """Ensure expected keybindings are registered."""
    from nvcli.ui.tui import NvCLIApp
    keys = {b.key for b in NvCLIApp.BINDINGS}
    assert "ctrl+c" in keys
    assert "ctrl+n" in keys


def test_tui_has_new_session_action():
    """Ensure action_new_session method exists on the app."""
    from nvcli.ui.tui import NvCLIApp
    assert hasattr(NvCLIApp, "action_new_session")
    assert callable(NvCLIApp.action_new_session)
