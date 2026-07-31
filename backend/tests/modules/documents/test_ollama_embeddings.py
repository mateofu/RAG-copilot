import httpx
import pytest

from app.modules.documents.application.embeddings import (
    EMBEDDING_DIMENSIONS,
    EmbeddingProviderError,
)
from app.modules.documents.infrastructure.embeddings.ollama import OllamaEmbeddingProvider


async def test_ollama_embeds_batch_and_validates_dimensions() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embed"
        assert b'"model":"bge-m3"' in request.content
        return httpx.Response(
            200,
            json={"embeddings": [[1.0] * EMBEDDING_DIMENSIONS] * 2},
        )

    provider = OllamaEmbeddingProvider(
        "http://ollama:11434",
        "bge-m3",
        5,
        transport=httpx.MockTransport(handler),
    )

    embeddings = await provider.embed(("primero", "segundo"))

    assert len(embeddings) == 2
    assert len(embeddings[0]) == EMBEDDING_DIMENSIONS


async def test_ollama_rejects_unexpected_dimensions() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"embeddings": [[1.0, 2.0]]})

    provider = OllamaEmbeddingProvider(
        "http://ollama:11434",
        "bge-m3",
        5,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmbeddingProviderError):
        await provider.embed(("texto",))


async def test_ollama_translates_http_failures() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    provider = OllamaEmbeddingProvider(
        "http://ollama:11434",
        "bge-m3",
        5,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmbeddingProviderError):
        await provider.embed(("texto",))
