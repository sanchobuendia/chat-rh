from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.app_models import User
from app.schemas.user import UserCreate


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def create(self, payload: UserCreate) -> User:
        user = User(**payload.model_dump())
        self.db.add(user)
        self.db.flush()
        return user

    def list_all(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.id)).all())

    def deactivate(self, user: User) -> None:
        user.is_active = False
