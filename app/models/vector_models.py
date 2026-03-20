from datetime import datetime
from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from app.core.config import get_settings

settings = get_settings()


class VectorBase(DeclarativeBase):
    pass


class Document(VectorBase):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    base_id: Mapped[int] = mapped_column(Integer, index=True)
    title: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(String(500))
    classification: Mapped[str] = mapped_column(String(64), default="internal")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Chunk(VectorBase):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    base_id: Mapped[int] = mapped_column(Integer, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dimension))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
