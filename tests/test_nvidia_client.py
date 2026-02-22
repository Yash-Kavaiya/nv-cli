"""Async tests for nvcli.nvidia_client using respx to mock HTTP calls."""
from __future__ import annotations

import json
import pytest
import respx
import httpx

from nvcli.config import Config
from nvcli.nvidia_client import NvidiaClient


MODELS_RESPONSE = {
    "object": "list",
    "data": [
        {"id": "meta/llama-3.1-70b-instruct", "object": "model"},
        {"id": "meta/llama-3.1-405b-instruct", "object": "model"},
        {"id": "nvidia/nemotron-4-340b-instruct", "object": "model"},
    ],
}

BASE_URL = "https://integrate.api.nvidia.com/v1"


@pytest.fixture
def cfg():
    return Config(
        api_key="nvapi-test1234567890",
        base_url=BASE_URL,
        model="meta/llama-3.1-70b-instruct",
        temperature=0.2,
        max_tokens=4096,
    )


@respx.mock
async def test_list_models_success(cfg):
    respx.get(f"{BASE_URL}/models").mock(
        return_value=httpx.Response(200, json=MODELS_RESPONSE)
    )
    client = NvidiaClient(cfg)
    models = await client.list_models()
    assert isinstance(models, list)
    assert len(models) == 3
    assert "meta/llama-3.1-70b-instruct" in models
    assert models == sorted(models)


@respx.mock
async def test_check_auth_success(cfg):
    respx.get(f"{BASE_URL}/models").mock(
        return_value=httpx.Response(200, json=MODELS_RESPONSE)
    )
    client = NvidiaClient(cfg)
    result = await client.check_auth()
    assert result is True


@respx.mock
async def test_check_auth_failure_401(cfg):
    respx.get(f"{BASE_URL}/models").mock(
        return_value=httpx.Response(
            401,
            json={"error": {"message": "Invalid API key", "type": "invalid_request_error"}},
        )
    )
    client = NvidiaClient(cfg)
    result = await client.check_auth()
    assert result is False


@respx.mock
async def test_check_auth_failure_network_error(cfg):
    respx.get(f"{BASE_URL}/models").mock(side_effect=httpx.ConnectError("Connection refused"))
    client = NvidiaClient(cfg)
    result = await client.check_auth()
    assert result is False


@respx.mock
async def test_list_models_returns_sorted(cfg):
    unsorted_response = {
        "object": "list",
        "data": [
            {"id": "z-model", "object": "model"},
            {"id": "a-model", "object": "model"},
            {"id": "m-model", "object": "model"},
        ],
    }
    respx.get(f"{BASE_URL}/models").mock(
        return_value=httpx.Response(200, json=unsorted_response)
    )
    client = NvidiaClient(cfg)
    models = await client.list_models()
    assert models == ["a-model", "m-model", "z-model"]


@respx.mock
async def test_complete_chat_returns_string(cfg):
    chat_response = {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello, world!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
    }
    respx.post(f"{BASE_URL}/chat/completions").mock(
        return_value=httpx.Response(200, json=chat_response)
    )
    client = NvidiaClient(cfg)
    messages = [{"role": "user", "content": "Say hello"}]
    result = await client.complete_chat(messages)
    assert result == "Hello, world!"




async def test_stream_chat_yields_tokens(cfg):
    """Test stream_chat yields token strings from delta content."""
    from unittest.mock import MagicMock, patch

    def make_chunk(text):
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta = MagicMock()
        chunk.choices[0].delta.content = text
        return chunk

    chunk_list = [make_chunk("Hello"), make_chunk(" world"), make_chunk(None)]

    class FakeAsyncStream:
        def __aiter__(self):
            return self._gen()

        async def _gen(self):
            for c in chunk_list:
                yield c

    async def fake_create(**kwargs):
        return FakeAsyncStream()

    client = NvidiaClient(cfg)
    with patch.object(client._client.chat.completions, "create", side_effect=fake_create):
        messages = [{"role": "user", "content": "Say hello world"}]
        tokens = []
        async for token in client.stream_chat(messages):
            tokens.append(token)

    assert "Hello" in tokens
    assert " world" in tokens
    assert None not in tokens
