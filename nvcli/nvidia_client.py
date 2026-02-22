"""Async client for NVIDIA's OpenAI-compatible API."""
from __future__ import annotations

from typing import AsyncGenerator, Optional

from openai import AsyncOpenAI, APIConnectionError, APIError, AuthenticationError

from nvcli.config import Config, load_config


class NvidiaClient:
    """Async wrapper around the NVIDIA NIM / OpenAI-compatible endpoint."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = AsyncOpenAI(
            api_key=config.api_key or "no-key-set",
            base_url=config.base_url,
        )

    async def stream_chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion, yielding individual token strings."""
        effective_model = model or self._config.model
        effective_temp = temperature if temperature is not None else self._config.temperature

        try:
            stream = await self._client.chat.completions.create(
                model=effective_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=effective_temp,
                max_tokens=self._config.max_tokens,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except AuthenticationError as exc:
            raise RuntimeError(
                "Authentication failed. Check that your NVIDIA API key is correct "
                "and starts with 'nvapi-'. Run 'nv auth set-key' to update it."
            ) from exc
        except APIConnectionError as exc:
            raise RuntimeError(
                f"NVIDIA API connection error: {exc}"
            ) from exc
        except APIError as exc:
            raise RuntimeError(
                f"NVIDIA API error ({exc.status_code}): {exc.message}"
            ) from exc

    async def complete_chat(
        self,
        messages: list[dict],
        model: str | None = None,
    ) -> str:
        """Non-streaming chat completion. Returns the full response as a string."""
        effective_model = model or self._config.model

        try:
            response = await self._client.chat.completions.create(
                model=effective_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                stream=False,
            )
            return response.choices[0].message.content or ""
        except AuthenticationError as exc:
            raise RuntimeError(
                "Authentication failed. Check that your NVIDIA API key is correct "
                "and starts with 'nvapi-'. Run 'nv auth set-key' to update it."
            ) from exc
        except APIConnectionError as exc:
            raise RuntimeError(
                f"NVIDIA API connection error: {exc}"
            ) from exc
        except APIError as exc:
            raise RuntimeError(
                f"NVIDIA API error ({exc.status_code}): {exc.message}"
            ) from exc

    async def list_models(self) -> list[str]:
        """Return a sorted list of model IDs available on the endpoint."""
        try:
            models_page = await self._client.models.list()
            return sorted(m.id for m in models_page.data)
        except AuthenticationError as exc:
            raise RuntimeError(
                "Authentication failed. Check your NVIDIA API key with 'nv auth check'."
            ) from exc
        except APIConnectionError as exc:
            raise RuntimeError(
                f"NVIDIA API connection error: {exc}"
            ) from exc
        except APIError as exc:
            raise RuntimeError(
                f"NVIDIA API error ({exc.status_code}): {exc.message}"
            ) from exc

    async def check_auth(self) -> bool:
        """Return True if the API key is valid, False otherwise."""
        try:
            await self.list_models()
            return True
        except RuntimeError:
            return False


_default_client: Optional[NvidiaClient] = None


def get_client(config: Config | None = None) -> NvidiaClient:
    """Factory that returns a (cached) NvidiaClient.

    Pass a Config explicitly in tests; otherwise uses the global loaded config.
    """
    global _default_client
    if config is not None:
        return NvidiaClient(config)
    if _default_client is None:
        _default_client = NvidiaClient(load_config())
    return _default_client
