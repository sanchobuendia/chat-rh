import io
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

from app.api import deps
from app.api.routes import admin_bases, admin_users, chat, ingestion, payroll
from app.schemas.auth import AuthContext
from app.schemas.base import BaseCreate, GrantAccessRequest, RevokeAccessRequest
from app.schemas.chat import ChatRequest
from app.schemas.user import UserCreate


def make_user(role="admin"):
    return AuthContext(
        user_id=1,
        email="admin@example.com",
        full_name="Admin User",
        role=role,
        department="RH",
        is_manager=True,
    )


def test_get_current_user_requires_header():
    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(x_user_email=None, db=object())

    assert exc.value.status_code == 401


def test_get_current_user_rejects_missing_or_inactive_user(monkeypatch):
    class FakeUserRepository:
        def __init__(self, db):
            self.db = db

        def get_by_email(self, email):
            return SimpleNamespace(
                id=1,
                email=email,
                full_name="Ana",
                role="employee",
                department="RH",
                is_manager=False,
                is_active=False,
            )

    monkeypatch.setattr(deps, "UserRepository", FakeUserRepository)

    with pytest.raises(HTTPException) as exc:
        deps.get_current_user(x_user_email="ana@example.com", db=object())

    assert exc.value.status_code == 403


def test_get_current_user_and_admin_user(monkeypatch):
    class FakeUserRepository:
        def __init__(self, db):
            self.db = db

        def get_by_email(self, email):
            return SimpleNamespace(
                id=1,
                email=email,
                full_name="Ana",
                role="hr_admin",
                department="RH",
                is_manager=True,
                is_active=True,
            )

    monkeypatch.setattr(deps, "UserRepository", FakeUserRepository)
    ctx = deps.get_current_user(x_user_email="ana@example.com", db=object())

    assert deps.get_admin_user(ctx).role == "hr_admin"

    with pytest.raises(HTTPException):
        deps.get_admin_user(ctx.model_copy(update={"role": "employee"}))


def test_chat_route_returns_service_result(monkeypatch):
    expected = SimpleNamespace(answer="ok", route="rag", citations=[])

    class FakeChatService:
        def __init__(self, app_db, vector_db):
            self.app_db = app_db
            self.vector_db = vector_db

        def run(self, payload, user):
            assert payload.question == "Oi"
            assert user.email == "admin@example.com"
            return expected

    monkeypatch.setattr(chat, "ChatService", FakeChatService)

    result = chat.chat(ChatRequest(question="Oi"), make_user(), object(), object())

    assert result is expected


def test_payroll_route_returns_result_or_404(monkeypatch):
    response = SimpleNamespace(employee_name="Ana")

    class FakePayrollService:
        def __init__(self, db):
            self.db = db

        def lookup_employee(self, employee_name, requester):
            return response if employee_name == "Ana" else None

    monkeypatch.setattr(payroll, "PayrollService", FakePayrollService)

    assert payroll.payroll_employee_lookup("Ana", make_user(), object()) is response
    with pytest.raises(HTTPException) as exc:
        payroll.payroll_employee_lookup("Bob", make_user(), object())
    assert exc.value.status_code == 404


def test_admin_users_routes(monkeypatch):
    class FakeRepo:
        def __init__(self, db):
            self.db = db
            self._users = db.users

        def get_by_email(self, email):
            return self._users.get(email)

        def create(self, payload):
            user = SimpleNamespace(
                id=2,
                email=payload.email,
                full_name=payload.full_name,
                role=payload.role,
                department=payload.department,
                is_manager=payload.is_manager,
                is_active=True,
            )
            self._users[payload.email] = user
            return user

        def get(self, user_id):
            return next((user for user in self._users.values() if user.id == user_id), None)

        def deactivate(self, user):
            user.is_active = False

        def list_all(self):
            return list(self._users.values())

    db = SimpleNamespace(users={}, commit=lambda: None, refresh=lambda _: None)
    monkeypatch.setattr(admin_users, "UserRepository", FakeRepo)

    created = admin_users.create_user(UserCreate(email="ana@example.com", full_name="Ana"), make_user(), db)
    assert created.email == "ana@example.com"

    with pytest.raises(HTTPException) as exc:
        admin_users.create_user(UserCreate(email="ana@example.com", full_name="Ana"), make_user(), db)
    assert exc.value.status_code == 409

    listed = admin_users.list_users(make_user(), db)
    assert [item.email for item in listed] == ["ana@example.com"]

    result = admin_users.deactivate_user(2, make_user(), db)
    assert result == {"status": "deactivated", "user_id": 2}

    with pytest.raises(HTTPException) as exc:
        admin_users.deactivate_user(99, make_user(), db)
    assert exc.value.status_code == 404


def test_admin_bases_routes(monkeypatch):
    class FakeUserRepo:
        def __init__(self, db):
            self.db = db

        def get_by_email(self, email):
            return self.db.users.get(email)

    class FakeBaseRepo:
        def __init__(self, db):
            self.db = db

        def create(self, payload):
            base = SimpleNamespace(
                id=7,
                name=payload.name,
                slug=payload.slug,
                description=payload.description,
                classification=payload.classification,
                is_active=True,
            )
            self.db.bases[payload.slug] = base
            return base

        def list_all(self):
            return list(self.db.bases.values())

        def get_by_slug(self, slug):
            return self.db.bases.get(slug)

        def grant_user_access(self, user_id, base_id):
            self.db.events.append(("grant", user_id, base_id))

        def revoke_user_access(self, user_id, base_id):
            self.db.events.append(("revoke", user_id, base_id))

    db = SimpleNamespace(
        users={"ana@example.com": SimpleNamespace(id=2, email="ana@example.com")},
        bases={},
        events=[],
        commit=lambda: None,
        refresh=lambda _: None,
    )
    monkeypatch.setattr(admin_bases, "UserRepository", FakeUserRepo)
    monkeypatch.setattr(admin_bases, "BaseRepository", FakeBaseRepo)

    created = admin_bases.create_base(BaseCreate(name="RH", slug="rh"), make_user(), db)
    assert created.slug == "rh"
    assert [item.slug for item in admin_bases.list_bases(make_user(), db)] == ["rh"]

    granted = admin_bases.grant_access(GrantAccessRequest(email="ana@example.com", slug="rh"), make_user(), db)
    revoked = admin_bases.revoke_access(RevokeAccessRequest(email="ana@example.com", slug="rh"), make_user(), db)

    assert granted["status"] == "granted"
    assert revoked["status"] == "revoked"

    with pytest.raises(HTTPException) as exc:
        admin_bases.grant_access(GrantAccessRequest(email="missing@example.com", slug="rh"), make_user(), db)
    assert exc.value.status_code == 404


def test_ingestion_upload_route_and_seed(monkeypatch, tmp_path):
    uploaded_jobs = []

    class FakeIngestionService:
        def __init__(self, app_db, vector_db):
            self.app_db = app_db
            self.vector_db = vector_db
            self.parser = SimpleNamespace(list_supported_files=lambda source_dir: [source_dir / "a.txt", source_dir / "b.txt"])

        def ingest_file(self, **kwargs):
            uploaded_jobs.append(kwargs)
            return SimpleNamespace(
                id=len(uploaded_jobs),
                file_name=kwargs["file_path"].name,
                title=kwargs["title"],
                base_id=kwargs["base_id"],
                classification=kwargs["classification"],
                status="completed",
                uploaded_by=kwargs["uploaded_by"],
            )

    class FakeBaseRepository:
        def __init__(self, db):
            self.db = db

        def list_all(self):
            return [SimpleNamespace(id=3, slug="rh-geral")]

    monkeypatch.setattr(ingestion, "IngestionService", FakeIngestionService)
    monkeypatch.setattr(ingestion, "BaseRepository", FakeBaseRepository)
    monkeypatch.setattr(ingestion.settings, "ingestion_source_dir", str(tmp_path))
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")

    upload = UploadFile(filename="doc.txt", file=io.BytesIO(b"content"))
    job = ingestion.upload_document(3, "Doc", "internal", upload, make_user(), object(), object())

    assert job.file_name == "doc.txt"

    seeded = ingestion.ingest_seed_documents(make_user(), object(), object())
    assert seeded == {"status": "ok", "ingested": 2}


def test_ingestion_seed_route_validates_missing_resources(monkeypatch, tmp_path):
    class FakeBaseRepository:
        def __init__(self, db):
            self.db = db

        def list_all(self):
            return []

    monkeypatch.setattr(ingestion, "BaseRepository", FakeBaseRepository)
    monkeypatch.setattr(ingestion.settings, "ingestion_source_dir", str(tmp_path / "missing"))

    with pytest.raises(HTTPException) as exc:
        ingestion.ingest_seed_documents(make_user(), object(), object())
    assert exc.value.status_code == 404

    source_dir = tmp_path / "seed"
    source_dir.mkdir()
    monkeypatch.setattr(ingestion.settings, "ingestion_source_dir", str(source_dir))
    with pytest.raises(HTTPException) as exc:
        ingestion.ingest_seed_documents(make_user(), object(), object())
    assert exc.value.status_code == 404
