import logging
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session
from app.models.vector_models import Chunk, Document

logger = logging.getLogger(__name__)


class VectorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_document_by_source_path(self, base_id: int, source_path: str) -> Document | None:
        stmt = select(Document).where(
            Document.base_id == base_id,
            Document.source_path == source_path,
        )
        return self.db.scalar(stmt)

    def delete_document_by_source_path(self, base_id: int, source_path: str) -> bool:
        document = self.get_document_by_source_path(base_id=base_id, source_path=source_path)
        if document is None:
            return False
        self.db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        self.db.execute(delete(Document).where(Document.id == document.id))
        self.db.flush()
        return True

    def create_document(self, base_id: int, title: str, source_path: str, classification: str) -> Document:
        doc = Document(base_id=base_id, title=title, source_path=source_path, classification=classification)
        self.db.add(doc)
        self.db.flush()
        return doc

    def create_chunk(self, document_id: int, base_id: int, chunk_index: int, content: str, embedding: list[float]) -> Chunk:
        chunk = Chunk(
            document_id=document_id,
            base_id=base_id,
            chunk_index=chunk_index,
            content=content,
            embedding=embedding,
        )
        self.db.add(chunk)
        self.db.flush()
        return chunk

    def similarity_search(
        self,
        query_embedding: list[float],
        allowed_base_ids: list[int],
        top_k: int = 4,
        search_query: str | None = None,
    ) -> list[dict]:
        if not allowed_base_ids:
            return []
        sql = text(
            """
            SELECT
                c.id AS chunk_id,
                c.document_id,
                d.title,
                c.content,
                c.embedding <=> CAST(:embedding AS vector) AS distance
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.base_id = ANY(:base_ids)
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
            """
        )
        rows = self.db.execute(
            sql,
            {
                "embedding": str(query_embedding),
                "base_ids": allowed_base_ids,
                "top_k": top_k,
            },
        ).mappings().all()
        logger.debug(
            "vector_similarity_search query=%r base_ids=%s top_k=%s rows=%s",
            search_query,
            allowed_base_ids,
            top_k,
            len(rows),
        )
        return [dict(r) for r in rows]
