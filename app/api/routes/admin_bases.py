from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_admin_user
from app.db.session import get_app_db
from app.repositories.base_repository import BaseRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthContext
from app.schemas.base import BaseCreate, BaseRead, GrantAccessRequest, RevokeAccessRequest

router = APIRouter()


@router.post("", response_model=BaseRead)
def create_base(
    payload: BaseCreate,
    _: AuthContext = Depends(get_admin_user),
    db: Session = Depends(get_app_db),
) -> BaseRead:
    repo = BaseRepository(db)
    base = repo.create(payload)
    db.commit()
    db.refresh(base)
    return BaseRead.model_validate(base)


@router.get("", response_model=list[BaseRead])
def list_bases(
    _: AuthContext = Depends(get_admin_user),
    db: Session = Depends(get_app_db),
) -> list[BaseRead]:
    return [BaseRead.model_validate(b) for b in BaseRepository(db).list_all()]


@router.post("/grant")
def grant_access(
    payload: GrantAccessRequest,
    _: AuthContext = Depends(get_admin_user),
    db: Session = Depends(get_app_db),
) -> dict:
    user_repo = UserRepository(db)
    base_repo = BaseRepository(db)
    user = user_repo.get_by_email(payload.email)
    base = base_repo.get_by_slug(payload.slug)
    if not user or not base:
        raise HTTPException(status_code=404, detail="User or base not found")
    base_repo.grant_user_access(user.id, base.id)
    db.commit()
    return {"status": "granted", "email": user.email, "slug": base.slug}


@router.post("/revoke")
def revoke_access(
    payload: RevokeAccessRequest,
    _: AuthContext = Depends(get_admin_user),
    db: Session = Depends(get_app_db),
) -> dict:
    user_repo = UserRepository(db)
    base_repo = BaseRepository(db)
    user = user_repo.get_by_email(payload.email)
    base = base_repo.get_by_slug(payload.slug)
    if not user or not base:
        raise HTTPException(status_code=404, detail="User or base not found")
    base_repo.revoke_user_access(user.id, base.id)
    db.commit()
    return {"status": "revoked", "email": user.email, "slug": base.slug}
