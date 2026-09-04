"""Embeddings provider supporting local sentence-transformers and OpenAI embeddings."""

import asyncio

import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

from evalforge.config import get_settings

logger = structlog.get_logger(__name__)


class EmbeddingClient:
    """Provides high-performance embedding calculations with model reuse and fallback."""

    def __init__(self, model_name: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        self._local_model: SentenceTransformer | None = None
        self._lock = asyncio.Lock()

    def _get_local_model(self) -> SentenceTransformer:
        if self._local_model is None:
            # Fallback model name if OpenAI model string is configured for local mode
            local_name = (
                self.model_name if "embedding" not in self.model_name else "all-MiniLM-L6-v2"
            )
            logger.info("loading_local_embedding_model", model=local_name)
            self._local_model = SentenceTransformer(local_name)
        return self._local_model

    async def embed_text(self, text: str) -> list[float]:
        """Generates embedding vector for a single text string."""
        vectors = await self.embed_batch([text])
        return vectors[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generates embeddings for a batch of strings using thread pool for CPU isolation."""
        if not texts:
            return []

        async with self._lock:
            model = self._get_local_model()
            embeddings = await asyncio.to_thread(
                model.encode,
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            return [vec.tolist() for vec in embeddings]

    @staticmethod
    def cosine_similarity(vec1: list[float] | np.ndarray, vec2: list[float] | np.ndarray) -> float:
        """Calculates cosine similarity between two normalized or raw vectors."""
        v1 = np.asarray(vec1, dtype=np.float32)
        v2 = np.asarray(vec2, dtype=np.float32)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))


_embedding_instance: EmbeddingClient | None = None


def get_embedding_client(model_name: str | None = None) -> EmbeddingClient:
    """Get or instantiate singleton EmbeddingClient."""
    global _embedding_instance
    if _embedding_instance is None:
        _embedding_instance = EmbeddingClient(model_name=model_name)
    return _embedding_instance
