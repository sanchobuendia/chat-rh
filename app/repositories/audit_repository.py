from sqlalchemy.orm import Session
from app.models.app_models import AuditEvent


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(self, user_email: str, action: str, query_text: str | None = None, result_summary: str | None = None) -> None:
        self.db.add(
            AuditEvent(
                user_email=user_email,
                action=action,
                query_text=query_text,
                result_summary=result_summary,
            )
        )
        self.db.flush()
