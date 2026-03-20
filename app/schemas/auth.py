from pydantic import BaseModel


class AuthContext(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: str
    department: str
    is_manager: bool
