from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.app_models import AppBase, AuditEvent, IngestionJob, KnowledgeBase, PayrollRecord, User, UserBaseAccess
from app.repositories.audit_repository import AuditRepository
from app.repositories.base_repository import BaseRepository
from app.repositories.ingestion_repository import IngestionRepository
from app.repositories.payroll_repository import PayrollRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthContext
from app.schemas.base import BaseCreate
from app.schemas.user import UserCreate
from app.services.ingestion_service import IngestionService
from app.services.payroll_service import PayrollService
from app.services.retrieval_service import RetrievalService


@pytest.fixture
def app_db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    AppBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()
    try:
        yield session
    finally:
        session.close()


def test_user_and_base_repositories_crud(app_db: Session):
    user_repo = UserRepository(app_db)
    base_repo = BaseRepository(app_db)

    user = user_repo.create(UserCreate(email="ana@example.com", full_name="Ana", is_manager=True))
    base = base_repo.create(BaseCreate(name="RH", slug="rh"))
    app_db.commit()

    assert user_repo.get(user.id).email == "ana@example.com"
    assert user_repo.get_by_email("ana@example.com").full_name == "Ana"
    assert [item.email for item in user_repo.list_all()] == ["ana@example.com"]

    base_repo.grant_user_access(user.id, base.id)
    base_repo.grant_user_access(user.id, base.id)
    assert base_repo.list_user_base_ids(user.id) == [base.id]

    base_repo.revoke_user_access(user.id, base.id)
    assert base_repo.list_user_base_ids(user.id) == []
    assert base_repo.get(base.id).slug == "rh"
    assert base_repo.get_by_slug("rh").name == "RH"
    assert [item.slug for item in base_repo.list_all()] == ["rh"]

    user_repo.deactivate(user)
    assert user.is_active is False


def test_audit_and_ingestion_repositories_create_records(app_db: Session):
    audit_repo = AuditRepository(app_db)
    ingestion_repo = IngestionRepository(app_db)
    base = KnowledgeBase(name="RH", slug="rh", classification="internal")
    app_db.add(base)
    app_db.flush()

    audit_repo.log("ana@example.com", "chat", "pergunta", "resposta")
    job = ingestion_repo.create_job(
        file_name="a.txt",
        title="A",
        base_id=base.id,
        classification="internal",
        status="completed",
        uploaded_by="tester",
    )
    app_db.commit()

    assert app_db.query(AuditEvent).one().action == "chat"
    assert app_db.get(IngestionJob, job.id).file_name == "a.txt"


def test_payroll_repository_finds_active_records_case_insensitive(app_db: Session):
    active = PayrollRecord(
        employee_name="Ana",
        document_number="12345678900",
        department="RH",
        role_title="Analista",
        manager_email="lead@example.com",
        monthly_salary=Decimal("1234.56"),
        currency="BRL",
        is_active=True,
    )
    inactive = PayrollRecord(
        employee_name="Ana",
        document_number="999",
        department="RH",
        role_title="Analista",
        manager_email="lead@example.com",
        monthly_salary=Decimal("10.00"),
        currency="BRL",
        is_active=False,
    )
    app_db.add_all([active, inactive])
    app_db.commit()

    record = PayrollRepository(app_db).find_by_employee_name("aNa")

    assert record.document_number == "12345678900"


def test_payroll_service_handles_miss_denied_and_success(monkeypatch):
    from app.services import payroll_service as module

    audit_calls = []

    class FakeAuditRepository:
        def __init__(self, db):
            self.db = db

        def log(self, *args):
            audit_calls.append(args)

    class FakePayrollRepository:
        def __init__(self, db):
            self.db = db

        def find_by_employee_name(self, employee_name):
            for record in getattr(self.db, "records", []):
                if record.employee_name.lower() == employee_name.lower():
                    return record
            return None

    monkeypatch.setattr(module, "AuditRepository", FakeAuditRepository)
    monkeypatch.setattr(module, "PayrollRepository", FakePayrollRepository)

    requester = AuthContext(
        user_id=1,
        email="boss@example.com",
        full_name="Boss",
        role="employee",
        department="RH",
        is_manager=False,
    )
    denied_db = SimpleNamespace(records=[], commit=lambda: None)
    service = PayrollService(denied_db)

    assert service.lookup_employee("Ana", requester) is None

    record = SimpleNamespace(
        employee_name="Ana",
        document_number="12345678900",
        department="RH",
        role_title="Analista",
        manager_email="other@example.com",
        monthly_salary=Decimal("5000.00"),
        currency="BRL",
    )
    denied_db.records = [record]
    assert service.lookup_employee("Ana", requester) is None

    manager = requester.model_copy(update={"email": "other@example.com"})
    allowed = service.lookup_employee("Ana", manager)
    assert allowed.employee_name == "Ana"
    assert allowed.document_number_masked.endswith("-00")
    assert PayrollService._mask_document("12") == "***"
    assert len(audit_calls) == 3


def test_retrieval_service_returns_deduped_results(monkeypatch):
    from app.services import retrieval_service as module

    class FakeBaseRepository:
        def __init__(self, db):
            self.db = db

        def list_user_base_ids(self, user_id):
            return [10]

    class FakeVectorRepository:
        def __init__(self, db):
            self.db = db

        def similarity_search(self, query_embedding, allowed_base_ids, top_k, max_distance, search_query):
            if search_query == "q1":
                return [
                    {"chunk_id": 1, "document_id": 1, "title": "A", "content": "x", "distance": 0.1, "score": 0.9},
                    {"chunk_id": 2, "document_id": 1, "title": "A", "content": "y", "distance": 0.2, "score": 0.8},
                ]
            return [{"chunk_id": 1, "document_id": 1, "title": "A", "content": "x", "distance": 0.1, "score": 0.9}]

    class FakeEmbeddingService:
        def embed(self, text):
            return [0.1, 0.2]

    llm = SimpleNamespace(generate_search_queries=lambda question, count: ["q1", "q2"])
    monkeypatch.setattr(module, "BaseRepository", FakeBaseRepository)
    monkeypatch.setattr(module, "VectorRepository", FakeVectorRepository)
    monkeypatch.setattr(module, "EmbeddingService", FakeEmbeddingService)

    service = RetrievalService(app_db=object(), vector_db=object(), llm_service=llm)
    user = AuthContext(
        user_id=1,
        email="ana@example.com",
        full_name="Ana",
        role="employee",
        department="RH",
        is_manager=False,
    )

    results = service.search(user, "question", top_k=1)

    assert results == [{"chunk_id": 1, "document_id": 1, "title": "A", "content": "x", "distance": 0.1, "score": 0.9}]


def test_retrieval_service_returns_empty_when_threshold_filters_everything(monkeypatch):
    from app.services import retrieval_service as module

    class FakeBaseRepository:
        def __init__(self, db):
            self.db = db

        def list_user_base_ids(self, user_id):
            return [10]

    class FakeVectorRepository:
        def __init__(self, db):
            self.db = db

        def similarity_search(self, query_embedding, allowed_base_ids, top_k, max_distance, search_query):
            return []

    class FakeEmbeddingService:
        def embed(self, text):
            return [0.1, 0.2]

    llm = SimpleNamespace(generate_search_queries=lambda question, count: ["q1"])
    monkeypatch.setattr(module, "BaseRepository", FakeBaseRepository)
    monkeypatch.setattr(module, "VectorRepository", FakeVectorRepository)
    monkeypatch.setattr(module, "EmbeddingService", FakeEmbeddingService)

    service = RetrievalService(app_db=object(), vector_db=object(), llm_service=llm)
    user = AuthContext(
        user_id=1,
        email="ana@example.com",
        full_name="Ana",
        role="employee",
        department="RH",
        is_manager=False,
    )

    assert service.search(user, "question", top_k=1) == []


def test_retrieval_service_returns_empty_when_user_has_no_access(monkeypatch):
    from app.services import retrieval_service as module

    class FakeBaseRepository:
        def __init__(self, db):
            self.db = db

        def list_user_base_ids(self, user_id):
            return []

    monkeypatch.setattr(module, "BaseRepository", FakeBaseRepository)

    service = RetrievalService(app_db=object(), vector_db=object(), llm_service=SimpleNamespace())
    user = AuthContext(
        user_id=1,
        email="ana@example.com",
        full_name="Ana",
        role="employee",
        department="RH",
        is_manager=False,
    )

    assert service.search(user, "question") == []


def test_ingestion_service_ingests_file(monkeypatch, tmp_path):
    from app.services import ingestion_service as module

    calls = {"chunks": []}

    class FakeIngestionRepository:
        def __init__(self, db):
            self.db = db

        def create_job(self, **kwargs):
            return SimpleNamespace(id=5, **kwargs)

    class FakeVectorRepository:
        def __init__(self, db):
            self.db = db

        def delete_document_by_source_path(self, base_id, source_path):
            calls["deleted"] = (base_id, source_path)
            return True

        def create_document(self, base_id, title, source_path, classification):
            calls["document"] = (base_id, title, source_path, classification)
            return SimpleNamespace(id=9)

        def create_chunk(self, **kwargs):
            calls["chunks"].append(kwargs)
            return SimpleNamespace(id=len(calls["chunks"]))

    class FakeParser:
        def parse(self, file_path):
            return "first second third"

    class FakeChunker:
        def split(self, text):
            return ["first", "second"]

    class FakeEmbeddingService:
        def embed(self, text):
            return [len(text)]

    monkeypatch.setattr(module, "IngestionRepository", FakeIngestionRepository)
    monkeypatch.setattr(module, "VectorRepository", FakeVectorRepository)
    monkeypatch.setattr(module, "DocumentParser", FakeParser)
    monkeypatch.setattr(module, "ChunkerService", FakeChunker)
    monkeypatch.setattr(module, "EmbeddingService", FakeEmbeddingService)

    app_db = SimpleNamespace(commit=lambda: calls.setdefault("app_commit", True), refresh=lambda job: calls.setdefault("refresh", job))
    vector_db = SimpleNamespace(commit=lambda: calls.setdefault("vector_commit", True))
    file_path = tmp_path / "doc.txt"
    file_path.write_text("content", encoding="utf-8")

    job = IngestionService(app_db=app_db, vector_db=vector_db).ingest_file(
        file_path=file_path,
        base_id=1,
        title="Doc",
        classification="internal",
        uploaded_by="tester",
    )

    assert job.id == 5
    assert calls["deleted"] == (1, str(file_path))
    assert len(calls["chunks"]) == 2
    assert calls["vector_commit"] is True
    assert calls["refresh"].id == 5
