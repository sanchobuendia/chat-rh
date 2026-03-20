from pydantic import BaseModel


class PayrollLookupResponse(BaseModel):
    employee_name: str
    document_number_masked: str
    department: str
    role_title: str
    monthly_salary: float
    currency: str
