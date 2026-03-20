from functools import lru_cache

from app.core.config import get_settings

settings = get_settings()


@lru_cache(maxsize=1)
def get_embedder():
    provider = settings.embedding_provider.strip().lower()
    if provider == "local":
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(settings.embedding_model.strip())
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=settings.embedding_model.strip())
    if provider == "bedrock":
        from langchain_aws import BedrockEmbeddings

        return BedrockEmbeddings(model_id=settings.BEDROCK_EMBEDDING_MODEL_ID.strip())
    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")


class EmbeddingService:
    @property
    def _embedder(self):
        return get_embedder()

    def embed(self, text: str) -> list[float]:
        provider = settings.embedding_provider.strip().lower()
        if provider == "local":
            vector = self._embedder.encode(
                text,
                normalize_embeddings=True,
            )
            return vector.tolist()
        return list(self._embedder.embed_query(text))
