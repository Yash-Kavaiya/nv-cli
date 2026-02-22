"""Tests for nvcli.agent.memory (session persistence)."""
from __future__ import annotations

import json
import asyncio
from pathlib import Path

import pytest

from nvcli.agent.memory import load_session, save_session, list_sessions, clear_session


def _patch_session_dir(monkeypatch, tmp_path):
    """Redirect session storage to a temp directory for isolation."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    from nvcli import config as config_module
    from nvcli.config import Config
    import nvcli.agent.memory as memory_module
    fake_config = Config(api_key="nvapi-test", session_dir=sessions_dir)
    monkeypatch.setattr(config_module, "load_config", lambda: fake_config)
    monkeypatch.setattr(memory_module, "load_config", lambda: fake_config)
    return sessions_dir


class TestLoadSessionEmpty:
    def test_load_nonexistent_session_returns_empty_list(self, tmp_path, monkeypatch):
        """Loading a session that does not exist should return an empty list."""
        _patch_session_dir(monkeypatch, tmp_path)
        result = asyncio.run(load_session("nonexistent"))
        assert result == []

    def test_load_default_session_when_no_file_returns_empty_list(self, tmp_path, monkeypatch):
        """Loading the default last session when no file exists returns []."""
        _patch_session_dir(monkeypatch, tmp_path)
        result = asyncio.run(load_session())
        assert result == []


class TestSaveAndLoadSession:
    def test_roundtrip_single_message(self, tmp_path, monkeypatch):
        """Save then load should return the identical messages list."""
        _patch_session_dir(monkeypatch, tmp_path)
        messages = [{"role": "user", "content": "Hello"}]
        asyncio.run(save_session(messages))
        loaded = asyncio.run(load_session())
        assert loaded == messages

    def test_roundtrip_multi_turn_conversation(self, tmp_path, monkeypatch):
        """Multi-turn conversations should survive a save/load roundtrip."""
        _patch_session_dir(monkeypatch, tmp_path)
        messages = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "4"},
            {"role": "user", "content": "And 3+3?"},
            {"role": "assistant", "content": "6"},
        ]
        asyncio.run(save_session(messages))
        loaded = asyncio.run(load_session())
        assert loaded == messages

    def test_roundtrip_named_session(self, tmp_path, monkeypatch):
        """A named session should be independently stored and retrieved."""
        _patch_session_dir(monkeypatch, tmp_path)
        messages = [{"role": "user", "content": "Named session test"}]
        asyncio.run(save_session(messages, "mysession"))
        loaded = asyncio.run(load_session("mysession"))
        assert loaded == messages

    def test_save_writes_metadata(self, tmp_path, monkeypatch):
        """Saved file should include name, saved_at, message_count alongside messages."""
        sessions_dir = _patch_session_dir(monkeypatch, tmp_path)
        messages = [{"role": "user", "content": "test"}]
        asyncio.run(save_session(messages, "meta_test"))
        saved_file = sessions_dir / "meta_test.json"
        assert saved_file.exists()
        data = json.loads(saved_file.read_text(encoding="utf-8"))
        assert data["name"] == "meta_test"
        assert data["message_count"] == 1
        assert "saved_at" in data
        assert data["messages"] == messages

    def test_roundtrip_unicode_content(self, tmp_path, monkeypatch):
        """Unicode content should survive roundtrip."""
        _patch_session_dir(monkeypatch, tmp_path)
        messages = [{"role": "user", "content": "hello world unicode test"}]
        asyncio.run(save_session(messages))
        loaded = asyncio.run(load_session())
        assert loaded[0]["content"] == "hello world unicode test"


class TestLoadSessionListFormat:
    def test_handles_old_list_format(self, tmp_path, monkeypatch):
        """Old sessions stored as a bare JSON list should be loaded correctly."""
        sessions_dir = _patch_session_dir(monkeypatch, tmp_path)
        messages = [
            {"role": "user", "content": "legacy format"},
            {"role": "assistant", "content": "still works"},
        ]
        session_file = sessions_dir / "last.json"
        session_file.write_text(json.dumps(messages), encoding="utf-8")
        loaded = asyncio.run(load_session())
        assert loaded == messages

    def test_handles_corrupt_json_gracefully(self, tmp_path, monkeypatch):
        """A corrupt session file should return an empty list, not raise."""
        sessions_dir = _patch_session_dir(monkeypatch, tmp_path)
        session_file = sessions_dir / "last.json"
        session_file.write_text("{ not valid json [[[", encoding="utf-8")
        result = asyncio.run(load_session())
        assert result == []

    def test_handles_empty_messages_key(self, tmp_path, monkeypatch):
        """A new-format file with an empty messages list should return []."""
        sessions_dir = _patch_session_dir(monkeypatch, tmp_path)
        data = {"name": "last", "saved_at": "2026-01-01T00:00:00", "message_count": 0, "messages": []}
        session_file = sessions_dir / "last.json"
        session_file.write_text(json.dumps(data), encoding="utf-8")
        result = asyncio.run(load_session())
        assert result == []


class TestListSessions:
    def test_empty_directory_returns_empty_list(self, tmp_path, monkeypatch):
        """list_sessions() on an empty sessions directory returns []."""
        _patch_session_dir(monkeypatch, tmp_path)
        result = asyncio.run(list_sessions())
        assert result == []

    def test_lists_multiple_sessions_alphabetically(self, tmp_path, monkeypatch):
        """All saved sessions should appear in sorted order."""
        _patch_session_dir(monkeypatch, tmp_path)
        names = ["work", "alpha", "beta"]
        for name in names:
            asyncio.run(save_session([{"role": "user", "content": name}], name))
        result = asyncio.run(list_sessions())
        assert result == sorted(names)

    def test_lists_default_last_session(self, tmp_path, monkeypatch):
        """The default last session should appear in the list after saving."""
        _patch_session_dir(monkeypatch, tmp_path)
        asyncio.run(save_session([{"role": "user", "content": "hi"}]))
        result = asyncio.run(list_sessions())
        assert "last" in result

    def test_sessions_dir_missing_returns_empty_list(self, tmp_path, monkeypatch):
        """If the sessions directory does not exist at all, return []."""
        from nvcli import config as config_module
        from nvcli.config import Config
        import nvcli.agent.memory as memory_module
        missing_dir = tmp_path / "no_such_dir" / "sessions"
        fake_config = Config(api_key="nvapi-test", session_dir=missing_dir)
        monkeypatch.setattr(config_module, "load_config", lambda: fake_config)
        monkeypatch.setattr(memory_module, "load_config", lambda: fake_config)
        result = asyncio.run(list_sessions())
        assert result == []


class TestClearSession:
    def test_clear_existing_session_deletes_file(self, tmp_path, monkeypatch):
        """clear_session() should remove the session file from disk."""
        sessions_dir = _patch_session_dir(monkeypatch, tmp_path)
        asyncio.run(save_session([{"role": "user", "content": "bye"}]))
        session_file = sessions_dir / "last.json"
        assert session_file.exists()
        clear_session()
        assert not session_file.exists()

    def test_clear_nonexistent_session_does_not_raise(self, tmp_path, monkeypatch):
        """clear_session() on a missing session should be a no-op."""
        _patch_session_dir(monkeypatch, tmp_path)
        clear_session("does_not_exist")

    def test_clear_named_session(self, tmp_path, monkeypatch):
        """clear_session(name) should only delete the named session file."""
        sessions_dir = _patch_session_dir(monkeypatch, tmp_path)
        asyncio.run(save_session([{"role": "user", "content": "keep me"}], "keep"))
        asyncio.run(save_session([{"role": "user", "content": "delete me"}], "remove"))
        clear_session("remove")
        assert not (sessions_dir / "remove.json").exists()
        assert (sessions_dir / "keep.json").exists()
