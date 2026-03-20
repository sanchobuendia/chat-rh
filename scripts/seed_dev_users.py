import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.repositories.base_repository import BaseRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate

settings = get_settings()
logger = logging.getLogger("seed_dev_users")

DEV_USERS = [
    UserCreate(
        email="ana@empresa.com",
        full_name="Ana Oliveira",
        role="hr_admin",
        department="RH",
        is_manager=True,
    ),
    UserCreate(
        email="sanchobuendia@gmail.com",
        full_name="Aureliano Sancho Souza Paiva",
        role="hr_admin",
        department="RH",
        is_manager=True,
    ),
    UserCreate(
        email="carlos@empresa.com",
        full_name="Carlos Lima",
        role="manager",
        department="Engenharia",
        is_manager=True,
    ),
    UserCreate(
        email="joao@empresa.com",
        full_name="Joao Santos",
        role="employee",
        department="Engenharia",
        is_manager=False,
    ),
]


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def main() -> None:
    configure_logging()
    logger.info("Seeding development users")

    app_engine = create_engine(settings.DB_USERS, future=True)

    with Session(app_engine) as app_db:
        user_repo = UserRepository(app_db)
        base_repo = BaseRepository(app_db)

        default_base = next((base for base in base_repo.list_all() if base.slug == "rh-geral"), None)
        if default_base is None:
            raise RuntimeError("Base padrao 'rh-geral' nao encontrada. Rode bootstrap_all.py antes.")

        created_count = 0
        existing_count = 0
        granted_count = 0

        for user_payload in DEV_USERS:
            user = user_repo.get_by_email(user_payload.email)
            if user is None:
                user = user_repo.create(user_payload)
                created_count += 1
                logger.info("Created dev user: %s", user.email)
            else:
                existing_count += 1
                logger.info("Dev user already exists: %s", user.email)

            before_grants = set(base_repo.list_user_base_ids(user.id))
            base_repo.grant_user_access(user.id, default_base.id)
            after_grants = set(base_repo.list_user_base_ids(user.id))
            if default_base.id in after_grants and default_base.id not in before_grants:
                granted_count += 1
                logger.info("Granted base '%s' to %s", default_base.slug, user.email)

        app_db.commit()

    logger.info(
        "Dev user seed completed: created=%s existing=%s granted_base=%s",
        created_count,
        existing_count,
        granted_count,
    )


if __name__ == "__main__":
    main()
