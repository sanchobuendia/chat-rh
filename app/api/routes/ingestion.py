from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.api.deps import get_admin_user
from app.core.config import get_settings
from app.db.session import get_app_db, get_vector_db
from app.schemas.auth import AuthContext
from app.schemas.ingestion import IngestionJobRead
from app.repositories.base_repository import BaseRepository
from app.services.ingestion_service import IngestionService

router = APIRouter()
settings = get_settings()


@router.post("/upload", response_model=IngestionJobRead)
def upload_document(
    base_id: int = Form(...),
    title: str = Form(...),
    classification: str = Form("internal"),
    file: UploadFile = File(...),
    _: AuthContext = Depends(get_admin_user),
    app_db: Session = Depends(get_app_db),
    vector_db: Session = Depends(get_vector_db),
) -> IngestionJobRead:
    upload_dir = Path("/tmp/hr_uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / file.filename
    dest.write_bytes(file.file.read())

    service = IngestionService(app_db=app_db, vector_db=vector_db)
    job = service.ingest_file(
        file_path=dest,
        base_id=base_id,
        title=title,
        classification=classification,
        uploaded_by="api-upload",
    )
    return IngestionJobRead.model_validate(job)


@router.post("/seed")
def ingest_seed_documents(
    _: AuthContext = Depends(get_admin_user),
    app_db: Session = Depends(get_app_db),
    vector_db: Session = Depends(get_vector_db),
) -> dict:
    source_dir = Path(settings.ingestion_source_dir)
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail="Seed dir not found")
    default_base = next((base for base in BaseRepository(app_db).list_all() if base.slug == "rh-geral"), None)
    if default_base is None:
        raise HTTPException(status_code=404, detail="Default base 'rh-geral' not found")
    service = IngestionService(app_db=app_db, vector_db=vector_db)
    paths = service.parser.list_supported_files(source_dir)
    count = 0
    for path in paths:
        service.ingest_file(
            file_path=path,
            base_id=default_base.id,
            title=path.stem,
            classification="internal",
            uploaded_by="seed-script",
        )
        count += 1
    return {"status": "ok", "ingested": count}
