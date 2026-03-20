from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_admin_user
from app.db.session import get_app_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthContext
from app.schemas.user import UserCreate, UserRead

router = APIRouter()


@router.post("", response_model=UserRead)
def create_user(
    payload: UserCreate,
    _: AuthContext = Depends(get_admin_user),
    db: Session = Depends(get_app_db),
) -> UserRead:
    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="User already exists")
    user = repo.create(payload)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.delete("/{user_id}")
def deactivate_user(
    user_id: int,
    _: AuthContext = Depends(get_admin_user),
    db: Session = Depends(get_app_db),
) -> dict:
    repo = UserRepository(db)
    user = repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    repo.deactivate(user)
    db.commit()
    return {"status": "deactivated", "user_id": user_id}


@router.get("", response_model=list[UserRead])
def list_users(
    _: AuthContext = Depends(get_admin_user),
    db: Session = Depends(get_app_db),
) -> list[UserRead]:
    repo = UserRepository(db)
    return [UserRead.model_validate(u) for u in repo.list_all()]
