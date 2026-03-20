from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.app_models import PayrollRecord


class PayrollRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_employee_name(self, employee_name: str) -> PayrollRecord | None:
        stmt = select(PayrollRecord).where(
            func.lower(PayrollRecord.employee_name) == employee_name.lower(),
            PayrollRecord.is_active.is_(True),
        )
        return self.db.scalar(stmt)
