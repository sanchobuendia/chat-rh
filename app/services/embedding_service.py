import hashlib
import math
from app.core.config import get_settings

settings = get_settings()


class EmbeddingService:
    def embed(self, text: str) -> list[float]:
        if settings.embedding_provider == "local":
            return self._local_embedding(text)
        return self._local_embedding(text)

    def _local_embedding(self, text: str) -> list[float]:
        values: list[float] = []
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        for i in range(settings.embedding_dimension):
            b = seed[i % len(seed)]
            values.append((b / 255.0) * 2 - 1)
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]
