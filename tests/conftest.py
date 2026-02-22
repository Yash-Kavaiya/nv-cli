"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from nvcli.config import Config


@pytest.fixture
def mock_config():
    """Return a Config instance pre-populated with test values."""
    return Config(
        api_key="nvapi-test1234567890",
        base_url="https://integrate.api.nvidia.com/v1",
        model="meta/llama-3.1-70b-instruct",
        temperature=0.2,
        max_tokens=4096,
    )
