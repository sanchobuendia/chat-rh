from collections.abc import Generator
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_app_db, get_vector_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthContext


def get_current_user(
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
    db: Session = Depends(get_app_db),
) -> AuthContext:
    if not x_user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Email header",
        )
    user = UserRepository(db).get_by_email(x_user_email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found or inactive",
        )
    return AuthContext(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        department=user.department,
        is_manager=user.is_manager,
    )


def get_admin_user(ctx: AuthContext = Depends(get_current_user)) -> AuthContext:
    if ctx.role not in {"admin", "hr_admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return ctx
