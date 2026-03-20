from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import get_settings

settings = get_settings()

app_engine = create_engine(settings.DB_USERS, future=True)
vector_engine = create_engine(settings.DB_PGVECTOR, future=True)

AppSessionLocal = sessionmaker(bind=app_engine, autoflush=False, autocommit=False, future=True)
VectorSessionLocal = sessionmaker(bind=vector_engine, autoflush=False, autocommit=False, future=True)


def get_app_db() -> Generator[Session, None, None]:
    db = AppSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_vector_db() -> Generator[Session, None, None]:
    db = VectorSessionLocal()
    try:
        yield db
    finally:
        db.close()
