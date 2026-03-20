import logging
from pathlib import Path
from sqlalchemy.orm import Session
from app.repositories.ingestion_repository import IngestionRepository
from app.repositories.vector_repository import VectorRepository
from app.services.chunker_service import ChunkerService
from app.services.document_parser import DocumentParser
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, app_db: Session, vector_db: Session):
        self.app_db = app_db
        self.vector_db = vector_db
        self.ingestion_repo = IngestionRepository(app_db)
        self.vector_repo = VectorRepository(vector_db)
        self.parser = DocumentParser()
        self.chunker = ChunkerService()
        self.embedding = EmbeddingService()

    def ingest_file(self, file_path: Path, base_id: int, title: str, classification: str, uploaded_by: str):
        source_path = str(file_path)
        text = self.parser.parse(file_path)
        chunks = self.chunker.split(text)
        replaced_existing = self.vector_repo.delete_document_by_source_path(base_id=base_id, source_path=source_path)
        logger.debug(
            "ingestion_file base_id=%s source_path=%s title=%r chunks=%s replaced_existing=%s",
            base_id,
            source_path,
            title,
            len(chunks),
            replaced_existing,
        )
        document = self.vector_repo.create_document(
            base_id=base_id,
            title=title,
            source_path=source_path,
            classification=classification,
        )
        for idx, chunk in enumerate(chunks):
            emb = self.embedding.embed(chunk)
            self.vector_repo.create_chunk(
                document_id=document.id,
                base_id=base_id,
                chunk_index=idx,
                content=chunk,
                embedding=emb,
            )
        job = self.ingestion_repo.create_job(
            file_name=file_path.name,
            title=title,
            base_id=base_id,
            classification=classification,
            status="completed",
            uploaded_by=uploaded_by,
        )
        self.vector_db.commit()
        self.app_db.commit()
        self.app_db.refresh(job)
        return job
