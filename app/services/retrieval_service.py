import logging
from app.repositories.base_repository import BaseRepository
from app.repositories.vector_repository import VectorRepository
from app.schemas.auth import AuthContext
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RetrievalService:
    QUERY_COUNT = 3
    TOP_K_PER_QUERY = 3

    def __init__(self, app_db, vector_db, llm_service):
        self.app_db = app_db
        self.vector_db = vector_db
        self.base_repo = BaseRepository(app_db)
        self.vector_repo = VectorRepository(vector_db)
        self.embedding_service = EmbeddingService()
        self.llm_service = llm_service

    def search(self, user: AuthContext, question: str, top_k: int = 4) -> list[dict]:
        allowed_base_ids = self.base_repo.list_user_base_ids(user.user_id)
        logger.debug(
            "retrieval_allowed_bases user_id=%s email=%s base_ids=%s top_k=%s question=%r",
            user.user_id,
            user.email,
            allowed_base_ids,
            top_k,
            question,
        )
        if not allowed_base_ids:
            logger.debug("retrieval_skipped_no_access user_id=%s", user.user_id)
            return []

        optimized_queries = self.llm_service.generate_search_queries(question=question, count=self.QUERY_COUNT)
        all_results: list[dict] = []

        for query in optimized_queries:
            query_embedding = self.embedding_service.embed(query)
            query_results = self.vector_repo.similarity_search(
                query_embedding=query_embedding,
                allowed_base_ids=allowed_base_ids,
                top_k=self.TOP_K_PER_QUERY,
                search_query=query,
            )
            logger.debug(
                "retrieval_query_results user_id=%s query=%r count=%s",
                user.user_id,
                query,
                len(query_results),
            )
            all_results.extend(query_results)

        deduped_results: list[dict] = []
        seen_chunk_ids: set[int] = set()
        for item in all_results:
            chunk_id = item["chunk_id"]
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            deduped_results.append(item)

        logger.debug(
            "retrieval_similarity_results user_id=%s total=%s deduped=%s queries=%s",
            user.user_id,
            len(all_results),
            len(deduped_results),
            optimized_queries,
        )
        final_results = deduped_results[:top_k]
        logger.debug(
            "retrieval_final_results user_id=%s requested_top_k=%s returned=%s",
            user.user_id,
            top_k,
            len(final_results),
        )
        return final_results
