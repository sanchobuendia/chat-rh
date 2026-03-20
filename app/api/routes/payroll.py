from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_app_db
from app.schemas.auth import AuthContext
from app.schemas.payroll import PayrollLookupResponse
from app.services.payroll_service import PayrollService

router = APIRouter()


@router.get("/employee", response_model=PayrollLookupResponse)
def payroll_employee_lookup(
    employee_name: str = Query(...),
    user: AuthContext = Depends(get_current_user),
    db: Session = Depends(get_app_db),
) -> PayrollLookupResponse:
    service = PayrollService(db)
    result = service.lookup_employee(employee_name=employee_name, requester=user)
    if result is None:
        raise HTTPException(status_code=404, detail="Employee not found or access denied")
    return result
