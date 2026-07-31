from typing import Any

import httpx

from app.modules.documents.application.embeddings import (
    EMBEDDING_DIMENSIONS,
    EmbeddingProviderError,
)


class OllamaEmbeddingProvider:
    dimensions = EMBEDDING_DIMENSIONS
    provider_name = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self.model_name = model
        self._timeout = timeout_seconds
        self._transport = transport

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = await client.post(
                    "/api/embed",
                    json={"model": self._model, "input": list(texts)},
                )
                response.raise_for_status()
                payload: Any = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise EmbeddingProviderError from error

        raw_embeddings = payload.get("embeddings") if isinstance(payload, dict) else None
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(texts):
            raise EmbeddingProviderError("invalid embedding response")

        embeddings: list[tuple[float, ...]] = []
        for raw_embedding in raw_embeddings:
            if not isinstance(raw_embedding, list) or len(raw_embedding) != self.dimensions:
                raise EmbeddingProviderError("unexpected embedding dimensions")
            try:
                embeddings.append(tuple(float(value) for value in raw_embedding))
            except (TypeError, ValueError) as error:
                raise EmbeddingProviderError("invalid embedding values") from error
        return tuple(embeddings)
