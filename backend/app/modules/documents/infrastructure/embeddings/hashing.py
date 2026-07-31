import hashlib
import math
import re

from app.modules.documents.application.embeddings import EMBEDDING_DIMENSIONS

TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)


class HashingEmbeddingProvider:
    """Deterministic, dependency-free embeddings for local development and tests."""

    dimensions = EMBEDDING_DIMENSIONS
    provider_name = "hashing"
    model_name = "feature-hashing-v1"

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._embed_one(text) for text in texts)

    def _embed_one(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimensions
        for token in TOKEN_PATTERN.findall(text.casefold()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            value = int.from_bytes(digest)
            index = value % self.dimensions
            vector[index] += 1.0 if value & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return tuple(vector)
        return tuple(value / norm for value in vector)
