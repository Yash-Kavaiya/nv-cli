"""Configuration management for nvcli using pydantic-settings and YAML fallback."""
from __future__ import annotations

import os
import stat
import sys
import warnings
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_CONFIG_DIR = Path.home() / ".nvcli"
_SESSIONS_DIR = _CONFIG_DIR / "sessions"
_CONFIG_FILE = _CONFIG_DIR / "config.yaml"


def _ensure_dirs() -> None:
    """Create ~/.nvcli/ and ~/.nvcli/sessions/ if they do not exist."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _load_yaml_defaults() -> dict:
    """Load values from ~/.nvcli/config.yaml if it exists, else return empty dict."""
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            return data
        except yaml.YAMLError as exc:
            print(f"[warning] Could not parse config file {_CONFIG_FILE}: {exc}", file=sys.stderr)
            return {}
        except OSError as exc:
            print(f"[warning] Could not read config file {_CONFIG_FILE}: {exc}", file=sys.stderr)
            return {}
    return {}


class Config(BaseSettings):
    """Main configuration object for nvcli.

    Priority (highest to lowest):
      1. Environment variables (NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_MODEL, …)
      2. ~/.nvcli/config.yaml
      3. Defaults defined here
    """

    model_config = SettingsConfigDict(
        env_prefix="NVIDIA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    api_key: Optional[str] = Field(default=None)
    base_url: str = Field(default="https://integrate.api.nvidia.com/v1")
    model: str = Field(default="meta/llama-3.1-70b-instruct")
    temperature: float = Field(default=0.2)
    max_tokens: int = Field(default=4096)
    session_dir: Path = Field(default_factory=lambda: _SESSIONS_DIR)
    command_allowlist: list[str] = Field(default_factory=list)
    dry_run: bool = Field(default=False)

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        _ensure_dirs()


def get_config_path() -> Path:
    """Return the Path to the YAML config file."""
    return _CONFIG_FILE


def load_config() -> Config:
    """Load and return a Config instance.

    Merges YAML file values with environment variable overrides.
    pydantic-settings automatically handles env vars via the NVIDIA_ prefix.
    """
    _ensure_dirs()
    yaml_defaults = _load_yaml_defaults()

    # Map known yaml keys to Config field names
    field_map = {
        "api_key": "api_key",
        "base_url": "base_url",
        "model": "model",
        "temperature": "temperature",
        "max_tokens": "max_tokens",
        "session_dir": "session_dir",
        "command_allowlist": "command_allowlist",
        "dry_run": "dry_run",
    }

    init_kwargs: dict = {}
    for yaml_key, field_name in field_map.items():
        if yaml_key in yaml_defaults:
            init_kwargs[field_name] = yaml_defaults[yaml_key]

    return Config(**init_kwargs)


def save_config(config: Config) -> None:
    """Write config to ~/.nvcli/config.yaml.

    The API key is stored as-is (it is sensitive — users should protect the file).
    Display of the key is masked elsewhere.
    """
    _ensure_dirs()
    data: dict = {
        "base_url": config.base_url,
        "model": config.model,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "session_dir": str(config.session_dir),
        "command_allowlist": config.command_allowlist,
        "dry_run": config.dry_run,
    }
    if config.api_key:
        data["api_key"] = config.api_key

    with open(_CONFIG_FILE, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, default_flow_style=False, allow_unicode=True)

    # Restrict permissions to owner-only (rw-------) on POSIX systems
    if os.name != "nt":  # POSIX only (no-op on Windows anyway)
        _CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
