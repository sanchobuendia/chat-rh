from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "employee"
    department: str = "general"
    is_manager: bool = False


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    department: str
    is_manager: bool
    is_active: bool

    model_config = {"from_attributes": True}
