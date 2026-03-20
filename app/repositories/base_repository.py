from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.models.app_models import KnowledgeBase, UserBaseAccess
from app.schemas.base import BaseCreate


class BaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, payload: BaseCreate) -> KnowledgeBase:
        base = KnowledgeBase(**payload.model_dump())
        self.db.add(base)
        self.db.flush()
        return base

    def get(self, base_id: int) -> KnowledgeBase | None:
        return self.db.get(KnowledgeBase, base_id)

    def get_by_slug(self, slug: str) -> KnowledgeBase | None:
        return self.db.scalar(select(KnowledgeBase).where(KnowledgeBase.slug == slug))

    def list_all(self) -> list[KnowledgeBase]:
        return list(self.db.scalars(select(KnowledgeBase).order_by(KnowledgeBase.id)).all())

    def grant_user_access(self, user_id: int, base_id: int) -> None:
        exists = self.db.scalar(
            select(UserBaseAccess).where(
                UserBaseAccess.user_id == user_id,
                UserBaseAccess.base_id == base_id,
            )
        )
        if not exists:
            self.db.add(UserBaseAccess(user_id=user_id, base_id=base_id))
            self.db.flush()

    def revoke_user_access(self, user_id: int, base_id: int) -> None:
        self.db.execute(
            delete(UserBaseAccess).where(
                UserBaseAccess.user_id == user_id,
                UserBaseAccess.base_id == base_id,
            )
        )

    def list_user_base_ids(self, user_id: int) -> list[int]:
        stmt = select(UserBaseAccess.base_id).where(UserBaseAccess.user_id == user_id)
        return list(self.db.scalars(stmt).all())
