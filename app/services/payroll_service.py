import logging
from decimal import Decimal
from sqlalchemy.orm import Session
from app.repositories.audit_repository import AuditRepository
from app.repositories.payroll_repository import PayrollRepository
from app.schemas.auth import AuthContext
from app.schemas.payroll import PayrollLookupResponse

logger = logging.getLogger(__name__)


class PayrollService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PayrollRepository(db)
        self.audit = AuditRepository(db)

    def lookup_employee(self, employee_name: str, requester: AuthContext) -> PayrollLookupResponse | None:
        logger.debug(
            "payroll_lookup_start requester=%s role=%s is_manager=%s employee_name=%r",
            requester.email,
            requester.role,
            requester.is_manager,
            employee_name,
        )
        record = self.repo.find_by_employee_name(employee_name)
        if not record:
            logger.debug("payroll_lookup_result status=miss employee_name=%r", employee_name)
            self.audit.log(requester.email, "payroll_lookup_miss", employee_name, None)
            self.db.commit()
            return None

        can_view = requester.role in {"admin", "hr_admin"} or requester.is_manager or record.manager_email.lower() == requester.email.lower()
        logger.debug(
            "payroll_lookup_auth employee_name=%r can_view=%s manager_email=%s",
            employee_name,
            can_view,
            record.manager_email,
        )
        if not can_view:
            self.audit.log(requester.email, "payroll_lookup_denied", employee_name, None)
            self.db.commit()
            return None

        logger.debug(
            "payroll_lookup_result status=success employee_name=%r role_title=%r department=%r",
            employee_name,
            record.role_title,
            record.department,
        )
        self.audit.log(requester.email, "payroll_lookup", employee_name, f"{record.employee_name}/{record.role_title}")
        self.db.commit()
        return PayrollLookupResponse(
            employee_name=record.employee_name,
            document_number_masked=self._mask_document(record.document_number),
            department=record.department,
            role_title=record.role_title,
            monthly_salary=float(record.monthly_salary),
            currency=record.currency,
        )

    @staticmethod
    def _mask_document(value: str) -> str:
        digits = ''.join(ch for ch in value if ch.isdigit())
        if len(digits) < 4:
            return "***"
        return f"***.***.***-{digits[-2:]}"
