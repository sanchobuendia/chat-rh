from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.app_models import AppBase
from app.models.vector_models import VectorBase
from app.repositories.base_repository import BaseRepository
from app.schemas.base import BaseCreate
from app.services.ingestion_service import IngestionService

settings = get_settings()


def ensure_vector_extension(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def verify_tables(engine, required_tables: list[str], label: str) -> None:
    existing_tables = set(inspect(engine).get_table_names())
    missing_tables = [table for table in required_tables if table not in existing_tables]
    if missing_tables:
        raise RuntimeError(f"{label} missing tables after bootstrap: {missing_tables}")


def bootstrap_databases() -> None:
    app_engine = create_engine(settings.DB_USERS, future=True)
    vector_engine = create_engine(settings.DB_PGVECTOR, future=True)
    AppBase.metadata.create_all(app_engine)
    ensure_vector_extension(vector_engine)
    VectorBase.metadata.create_all(vector_engine)
    verify_tables(
        app_engine,
        [
            "users",
            "knowledge_bases",
            "user_base_access",
            "ingestion_jobs",
            "payroll_records",
            "audit_events",
        ],
        "app_db",
    )
    verify_tables(vector_engine, ["documents", "chunks"], "vector_db")


def seed_core_data(app_db: Session, vector_db: Session) -> None:
    base_repo = BaseRepository(app_db)

    existing = base_repo.list_all()
    if not existing:
        base_repo.create(
            BaseCreate(
                name="RH Geral",
                slug="rh-geral",
                description="Documentos gerais do RH",
                classification="internal",
            )
        )
        app_db.flush()

    app_db.commit()

    default_base = next((base for base in base_repo.list_all() if base.slug == "rh-geral"), None)
    if default_base is None:
        raise RuntimeError("Base padrao 'rh-geral' nao encontrada apos bootstrap")

    service = IngestionService(app_db=app_db, vector_db=vector_db)
    docs_dir = Path(settings.ingestion_source_dir)
    if docs_dir.exists():
        for path in service.parser.list_supported_files(docs_dir):
            service.ingest_file(
                path,
                base_id=default_base.id,
                title=path.stem,
                classification="internal",
                uploaded_by="bootstrap",
            )
