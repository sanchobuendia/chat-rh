import csv
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.models.app_models import AppBase, PayrollRecord
from app.models.vector_models import VectorBase
from app.repositories.base_repository import BaseRepository
from app.schemas.base import BaseCreate
from app.services.ingestion_service import IngestionService

settings = get_settings()
logger = logging.getLogger("bootstrap")


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def ensure_vector_extension(engine) -> None:
    logger.info("Ensuring pgvector extension on DB_PGVECTOR")
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


def verify_tables(engine, required_tables: list[str], label: str) -> None:
    existing_tables = set(inspect(engine).get_table_names())
    missing_tables = [table for table in required_tables if table not in existing_tables]
    if missing_tables:
        raise RuntimeError(f"{label} missing tables after bootstrap: {missing_tables}")
    logger.info("%s tables ready: %s", label, sorted(existing_tables.intersection(required_tables)))


def main() -> None:
    configure_logging()
    logger.info("Bootstrap started")
    app_engine = create_engine(settings.DB_USERS, future=True)
    vector_engine = create_engine(settings.DB_PGVECTOR, future=True)

    logger.info("Creating/validating schema on DB_USERS")
    AppBase.metadata.create_all(app_engine)
    logger.info("Creating/validating schema on DB_PGVECTOR")
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

    with Session(app_engine) as app_db, Session(vector_engine) as vector_db:
        base_repo = BaseRepository(app_db)

        logger.info("Ensuring default knowledge base exists")
        if not base_repo.list_all():
            base_repo.create(
                BaseCreate(
                    name="RH Geral",
                    slug="rh-geral",
                    description="Documentos gerais do RH",
                    classification="internal",
                )
            )
            app_db.commit()
            logger.info("Default knowledge base created")

        default_base = next((base for base in base_repo.list_all() if base.slug == "rh-geral"), None)
        if default_base is None:
            raise RuntimeError("Base padrao 'rh-geral' nao encontrada apos bootstrap")
        logger.info("Default knowledge base ready: id=%s slug=%s", default_base.id, default_base.slug)

        docs_dir = Path(settings.ingestion_source_dir)
        service = IngestionService(app_db=app_db, vector_db=vector_db)
        if docs_dir.exists():
            doc_paths = service.parser.list_supported_files(docs_dir)
            logger.info("Starting document ingestion from %s with %s file(s)", docs_dir, len(doc_paths))
            for index, path in enumerate(doc_paths, start=1):
                logger.info("Ingesting document %s/%s: %s", index, len(doc_paths), path.name)
                service.ingest_file(
                    path,
                    base_id=default_base.id,
                    title=path.stem,
                    classification="internal",
                    uploaded_by="bootstrap",
                )
            logger.info("Document ingestion completed")
        else:
            logger.warning("Document source dir not found: %s", docs_dir)

        payroll_csv = Path(settings.payroll_csv_path)
        if payroll_csv.exists():
            logger.info("Starting payroll seed from %s", payroll_csv)
            rows = list(csv.DictReader(payroll_csv.open(encoding="utf-8")))
            logger.info("Payroll CSV loaded with %s row(s)", len(rows))

            csv_document_numbers = {
                row["document_number"]
                for row in rows
                if row.get("document_number")
            }
            existing_document_numbers = set(
                app_db.scalars(
                    select(PayrollRecord.document_number).where(
                        PayrollRecord.document_number.in_(csv_document_numbers)
                    )
                ).all()
            )

            new_records = [
                PayrollRecord(
                    employee_name=row["employee_name"],
                    document_number=row["document_number"],
                    department=row["department"],
                    role_title=row["role_title"],
                    manager_email=row["manager_email"],
                    monthly_salary=row["monthly_salary"],
                    currency=row["currency"],
                    is_active=True,
                )
                for row in rows
                if row["document_number"] not in existing_document_numbers
            ]

            if new_records:
                app_db.add_all(new_records)
            app_db.commit()
            inserted_count = len(new_records)
            skipped_count = len(rows) - inserted_count
            logger.info("Payroll seed completed: inserted=%s skipped_existing=%s", inserted_count, skipped_count)
        else:
            logger.warning("Payroll CSV not found: %s", payroll_csv)

    logger.info("Bootstrap completed")


if __name__ == "__main__":
    main()
