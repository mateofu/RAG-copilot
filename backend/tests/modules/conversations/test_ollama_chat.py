import httpx
import pytest

from app.modules.conversations.application.chat import ChatProviderError
from app.modules.conversations.infrastructure.ollama import OllamaChatProvider


async def test_ollama_chat_returns_content_and_usage() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        assert b'"stream":false' in request.content
        assert b'"num_predict":128' in request.content
        return httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": " Respuesta [1]. "},
                "prompt_eval_count": 25,
                "eval_count": 6,
            },
        )

    provider = OllamaChatProvider(
        "http://ollama:11434",
        "qwen2.5:1.5b",
        5,
        128,
        1,
        transport=httpx.MockTransport(handler),
    )

    result = await provider.answer("system", "user")

    assert result.content == "Respuesta [1]."
    assert result.input_tokens == 25
    assert result.output_tokens == 6


async def test_ollama_chat_rejects_empty_response() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": " "}})

    provider = OllamaChatProvider(
        "http://ollama:11434",
        "qwen2.5:1.5b",
        5,
        128,
        1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ChatProviderError):
        await provider.answer("system", "user")
