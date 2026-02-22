"""Tests for nvcli.config."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from nvcli.config import Config, load_config, save_config, get_config_path


def _patch(monkeypatch, tmp_path):
    config_dir = tmp_path / ".nvcli"
    sessions_dir = config_dir / "sessions"
    config_file = config_dir / "config.yaml"
    monkeypatch.setattr("nvcli.config._CONFIG_DIR", config_dir)
    monkeypatch.setattr("nvcli.config._SESSIONS_DIR", sessions_dir)
    monkeypatch.setattr("nvcli.config._CONFIG_FILE", config_file)
    for var in ("NVIDIA_API_KEY", "NVIDIA_BASE_URL", "NVIDIA_MODEL",
                "NVIDIA_TEMPERATURE", "NVIDIA_MAX_TOKENS", "NVIDIA_DRY_RUN"):
        monkeypatch.delenv(var, raising=False)
    return config_dir, sessions_dir, config_file


class TestLoadConfigDefaults:
    def test_returns_config_instance(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        cfg = load_config()
        assert isinstance(cfg, Config)

    def test_default_base_url(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        cfg = load_config()
        assert cfg.base_url == "https://integrate.api.nvidia.com/v1"

    def test_default_model(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        cfg = load_config()
        assert cfg.model == "meta/llama-3.1-70b-instruct"

    def test_default_temperature(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        cfg = load_config()
        assert cfg.temperature == pytest.approx(0.2)

    def test_default_max_tokens(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        cfg = load_config()
        assert cfg.max_tokens == 4096

    def test_api_key_is_none_by_default(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        cfg = load_config()
        assert cfg.api_key is None


class TestEnvVarOverrides:
    def test_nvidia_api_key_env_var(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-env-key-9999")
        cfg = load_config()
        assert cfg.api_key == "nvapi-env-key-9999"

    def test_nvidia_base_url_env_var(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        monkeypatch.setenv("NVIDIA_BASE_URL", "https://custom.endpoint/v1")
        cfg = load_config()
        assert cfg.base_url == "https://custom.endpoint/v1"

    def test_nvidia_model_env_var(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        monkeypatch.setenv("NVIDIA_MODEL", "meta/llama-3.1-405b-instruct")
        cfg = load_config()
        assert cfg.model == "meta/llama-3.1-405b-instruct"


class TestSaveAndLoadRoundtrip:
    def test_roundtrip_api_key(self, tmp_path, monkeypatch):
        _, _, config_file = _patch(monkeypatch, tmp_path)
        original = Config(api_key="nvapi-roundtrip-1234")
        save_config(original)
        assert config_file.exists()
        loaded = load_config()
        assert loaded.api_key == "nvapi-roundtrip-1234"

    def test_roundtrip_model(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        original = Config(api_key="nvapi-test", model="meta/llama-3.1-405b-instruct")
        save_config(original)
        loaded = load_config()
        assert loaded.model == "meta/llama-3.1-405b-instruct"

    def test_roundtrip_temperature(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        original = Config(temperature=0.9)
        save_config(original)
        loaded = load_config()
        assert loaded.temperature == pytest.approx(0.9)

    def test_roundtrip_max_tokens(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        original = Config(max_tokens=1024)
        save_config(original)
        loaded = load_config()
        assert loaded.max_tokens == 1024

    def test_roundtrip_dry_run(self, tmp_path, monkeypatch):
        _patch(monkeypatch, tmp_path)
        original = Config(dry_run=True)
        save_config(original)
        loaded = load_config()
        assert loaded.dry_run is True

    def test_yaml_is_human_readable(self, tmp_path, monkeypatch):
        _, _, config_file = _patch(monkeypatch, tmp_path)
        original = Config(api_key="nvapi-readable-key", model="some/model")
        save_config(original)
        with open(config_file, "r") as fh:
            data = yaml.safe_load(fh)
        assert data["api_key"] == "nvapi-readable-key"
        assert data["model"] == "some/model"


class TestDirCreation:
    def test_dirs_created_by_load_config(self, tmp_path, monkeypatch):
        config_dir, sessions_dir, _ = _patch(monkeypatch, tmp_path)
        assert not config_dir.exists()
        load_config()
        assert config_dir.exists()
        assert sessions_dir.exists()

    def test_dirs_created_by_save_config(self, tmp_path, monkeypatch):
        config_dir, sessions_dir, _ = _patch(monkeypatch, tmp_path)
        assert not config_dir.exists()
        save_config(Config())
        assert config_dir.exists()


class TestCorruptYamlAndPermissions:
    def test_load_config_with_corrupt_yaml_falls_back_to_defaults(self, tmp_path, monkeypatch, capsys):
        """Corrupt YAML should fall back to defaults and print a warning to stderr."""
        config_dir, sessions_dir, config_file = _patch(monkeypatch, tmp_path)
        config_dir.mkdir(parents=True, exist_ok=True)
        sessions_dir.mkdir(parents=True, exist_ok=True)
        # Write corrupt (unparseable) YAML content
        config_file.write_text(": bad: yaml: [\n", encoding="utf-8")

        cfg = load_config()

        # Defaults should be returned despite the corrupt file
        assert cfg.base_url == "https://integrate.api.nvidia.com/v1"
        assert cfg.model == "meta/llama-3.1-70b-instruct"
        assert cfg.api_key is None

        # A warning should appear on stderr
        captured = capsys.readouterr()
        assert "warning" in captured.err.lower()

    def test_save_config_sets_restrictive_permissions_on_posix(self, tmp_path, monkeypatch):
        """On POSIX, saved config file should be mode 0o600."""
        import os
        import stat as stat_module

        if os.name == "nt":
            pytest.skip("Permission test is POSIX-only")

        _patch(monkeypatch, tmp_path)
        cfg = Config(api_key="nvapi-perm-test")
        save_config(cfg)

        config_file = get_config_path()
        file_mode = config_file.stat().st_mode
        # Check only the permission bits
        permissions = stat_module.S_IMODE(file_mode)
        assert permissions == 0o600, f"Expected 0o600, got {oct(permissions)}"
