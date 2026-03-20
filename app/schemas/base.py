from pydantic import BaseModel, EmailStr


class BaseCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None
    classification: str = "internal"


class BaseRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    classification: str
    is_active: bool

    model_config = {"from_attributes": True}


class GrantAccessRequest(BaseModel):
    email: EmailStr
    slug: str


class RevokeAccessRequest(BaseModel):
    email: EmailStr
    slug: str
