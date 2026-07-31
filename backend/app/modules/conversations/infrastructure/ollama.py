import asyncio
from typing import Any

import httpx

from app.modules.conversations.application.chat import ChatProviderError, ChatResult


class OllamaChatProvider:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        max_concurrency: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds
        self._transport = transport
        self._max_output_tokens = max_output_tokens
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def answer(self, system_prompt: str, user_prompt: str) -> ChatResult:
        async with self._semaphore:
            return await self._answer(system_prompt, user_prompt)

    async def _answer(self, system_prompt: str, user_prompt: str) -> ChatResult:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    "/api/chat",
                    json={
                        "model": self._model,
                        "stream": False,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "options": {
                            "temperature": 0.1,
                            "num_predict": self._max_output_tokens,
                        },
                    },
                )
                response.raise_for_status()
                payload: Any = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ChatProviderError from error
        if not isinstance(payload, dict):
            raise ChatProviderError("invalid chat response")
        message = payload.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ChatProviderError("empty chat response")
        return ChatResult(
            content=content.strip(),
            input_tokens=_non_negative_int(payload.get("prompt_eval_count")),
            output_tokens=_non_negative_int(payload.get("eval_count")),
        )


def _non_negative_int(value: object) -> int:
    return value if isinstance(value, int) and value >= 0 else 0
