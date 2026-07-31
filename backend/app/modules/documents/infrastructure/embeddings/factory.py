from app.core.config import Settings
from app.modules.documents.application.embeddings import EmbeddingProvider
from app.modules.documents.infrastructure.embeddings.hashing import HashingEmbeddingProvider
from app.modules.documents.infrastructure.embeddings.ollama import OllamaEmbeddingProvider


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "hashing":
        return HashingEmbeddingProvider()
    return OllamaEmbeddingProvider(
        base_url=settings.ollama_base_url,
        model=settings.embedding_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )
