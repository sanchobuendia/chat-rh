from sqlalchemy.orm import Session
from app.models.app_models import IngestionJob


class IngestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_job(self, **kwargs) -> IngestionJob:
        job = IngestionJob(**kwargs)
        self.db.add(job)
        self.db.flush()
        return job
