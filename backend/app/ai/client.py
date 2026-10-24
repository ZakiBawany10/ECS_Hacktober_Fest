"""Gemma, called through Ollama's chat API with structured JSON output."""

import json
from typing import Any, Protocol

import httpx

from .. import config


class GemmaError(Exception):
    """Gemma couldn't be reached or didn't reply with a JSON object."""


class ChatClient(Protocol):
    async def chat_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]: ...


class GemmaClient:
    def __init__(
        self,
        base_url: str = config.GEMMA_BASE_URL,
        model: str = config.GEMMA_MODEL,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.model = model
        self.http = http or httpx.AsyncClient(base_url=base_url, timeout=config.GEMMA_TIMEOUT_SECONDS)

    async def chat_json(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Return Gemma's reply as a JSON object shaped by schema, trying twice. Raises GemmaError."""
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,  # thinking is 5-7× slower and doesn't improve short headlines
            "keep_alive": config.GEMMA_KEEP_ALIVE,
            "format": schema,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        error: Exception | None = None
        for _ in range(2):
            try:
                response = await self.http.post("/api/chat", json=payload)
                response.raise_for_status()
                reply = json.loads(response.json()["message"]["content"])
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                error = exc
                continue
            if isinstance(reply, dict):
                return reply
            error = GemmaError(f"expected a JSON object, got {reply!r}")
        raise GemmaError(f"Gemma call failed: {error!r}") from error

    async def aclose(self) -> None:
        await self.http.aclose()
