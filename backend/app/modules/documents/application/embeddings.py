from typing import Protocol

EMBEDDING_DIMENSIONS = 1024


class EmbeddingProviderError(Exception):
    code = "embedding_provider_failed"


class EmbeddingProvider(Protocol):
    dimensions: int
    provider_name: str
    model_name: str

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...
