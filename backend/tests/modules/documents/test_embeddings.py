import math

import pytest

from app.modules.documents.application.embeddings import EMBEDDING_DIMENSIONS
from app.modules.documents.infrastructure.embeddings.hashing import HashingEmbeddingProvider


async def test_hashing_embeddings_are_deterministic_and_normalized() -> None:
    provider = HashingEmbeddingProvider()

    first, second = await provider.embed(("Contrato laboral", "Contrato laboral"))

    assert first == second
    assert len(first) == EMBEDDING_DIMENSIONS
    assert math.sqrt(sum(value * value for value in first)) == pytest.approx(1.0)


async def test_hashing_embeddings_preserve_shared_token_signal() -> None:
    provider = HashingEmbeddingProvider()
    query, related, unrelated = await provider.embed(
        ("vacaciones", "politica de vacaciones", "facturacion proveedores")
    )

    related_score = sum(left * right for left, right in zip(query, related, strict=True))
    unrelated_score = sum(left * right for left, right in zip(query, unrelated, strict=True))

    assert related_score > unrelated_score
