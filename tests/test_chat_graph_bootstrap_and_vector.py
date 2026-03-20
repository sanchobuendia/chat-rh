from types import SimpleNamespace

import pytest

from app.graph.builder import build_graph
from app.services.chat_service import ChatService
from app.services.llm_service import LLMService
from app.workers import bootstrap


class FakeCompiledGraph:
    def __init__(self, nodes):
        self.nodes = nodes

    def invoke(self, request_input, config):
        state = dict(request_input)
        state.update(self.nodes["router"](state))
        route = state["route"]
        state.update(self.nodes[route](state))
        state.update(self.nodes["finalize"](state))
        return state


class FakeGraph:
    def __init__(self, nodes):
        self.nodes = nodes
        self.checkpointer = None

    def compile(self, checkpointer=None):
        self.checkpointer = checkpointer
        return FakeCompiledGraph(self.nodes)


def fake_build_graph(router_node, rag_node, payroll_node, smalltalk_node, finalize_node):
    return FakeGraph(
        {
            "router": router_node,
            "rag": rag_node,
            "payroll": payroll_node,
            "smalltalk": smalltalk_node,
            "finalize": finalize_node,
        }
    )


def make_user():
    return SimpleNamespace(
        user_id=1,
        email="ana@example.com",
        full_name="Ana Silva",
        role="employee",
        department="RH",
        is_manager=False,
    )


def make_payload(question, top_k=3, thread_id="thread-1"):
    return SimpleNamespace(question=question, top_k=top_k, thread_id=thread_id)


def test_chat_service_run_rag_smalltalk_and_payroll(monkeypatch):
    from app.services import chat_service as module

    audit_log = []

    class FakeAuditRepository:
        def __init__(self, db):
            self.db = db

        def log(self, *args):
            audit_log.append(args)

    class FakeLLMService:
        def answer(self, question, retrieved_chunks, structured_result=None):
            if structured_result:
                return f"PAYROLL:{structured_result['employee_name']}"
            return f"RAG:{question}:{len(retrieved_chunks)}"

        def converse(self, question, user_name=None):
            return f"SMALLTALK:{user_name}:{question}"

    class FakeRouterService:
        def __init__(self, llm_service):
            self.llm_service = llm_service

        def route(self, question):
            if "salario" in question.lower():
                return "payroll"
            if "oi" in question.lower():
                return "smalltalk"
            return "rag"

    class FakeRetrievalService:
        def __init__(self, app_db, vector_db, llm_service):
            self.app_db = app_db
            self.vector_db = vector_db
            self.llm_service = llm_service

        def search(self, user, question, top_k):
            return [
                {"document_id": 1, "title": "Doc", "chunk_id": 9, "content": "Trecho relevante"},
            ]

    class FakePayrollService:
        def __init__(self, db):
            self.db = db

        def lookup_employee(self, employee_name, requester):
            if employee_name == "Ana":
                return SimpleNamespace(model_dump=lambda: {"employee_name": "Ana"})
            return None

    monkeypatch.setattr(module, "AuditRepository", FakeAuditRepository)
    monkeypatch.setattr(module, "LLMService", FakeLLMService)
    monkeypatch.setattr(module, "RouterService", FakeRouterService)
    monkeypatch.setattr(module, "RetrievalService", FakeRetrievalService)
    monkeypatch.setattr(module, "PayrollService", FakePayrollService)
    monkeypatch.setattr(module, "build_graph", fake_build_graph)
    monkeypatch.setattr(module, "PostgresSaver", None)

    commits = []
    service = ChatService(app_db=SimpleNamespace(commit=lambda: commits.append("commit")), vector_db=object())

    rag = service.run(make_payload("Me fale sobre férias"), make_user())
    smalltalk = service.run(make_payload("Oi time"), make_user())
    payroll_result = service.run(make_payload("Qual o salario de Ana?"), make_user())
    payroll_missing_name = service.run(make_payload("Qual o salario?"), make_user())

    assert rag.route == "rag"
    assert rag.citations[0].title == "Doc"
    assert smalltalk.answer.startswith("SMALLTALK:Ana")
    assert payroll_result.answer == "PAYROLL:Ana"
    assert "Informe o nome do colaborador" in payroll_missing_name.answer
    assert len(audit_log) == 4
    assert commits == ["commit", "commit", "commit", "commit"]


def test_chat_service_run_payroll_denied(monkeypatch):
    from app.services import chat_service as module

    monkeypatch.setattr(module, "AuditRepository", lambda db: SimpleNamespace(log=lambda *args: None))
    monkeypatch.setattr(module, "LLMService", lambda: SimpleNamespace(answer=lambda **kwargs: "unused", converse=lambda **kwargs: "unused"))
    monkeypatch.setattr(module, "RouterService", lambda llm: SimpleNamespace(route=lambda question: "payroll"))
    monkeypatch.setattr(module, "RetrievalService", lambda *args: SimpleNamespace(search=lambda **kwargs: []))
    monkeypatch.setattr(module, "PayrollService", lambda db: SimpleNamespace(lookup_employee=lambda employee_name, requester: None))
    monkeypatch.setattr(module, "build_graph", fake_build_graph)
    monkeypatch.setattr(module, "PostgresSaver", None)

    service = ChatService(app_db=SimpleNamespace(commit=lambda: None), vector_db=object())
    result = service.run(make_payload("Qual o salario de Ana?"), make_user())

    assert "Nao encontrei" in result.answer or "Não encontrei" in result.answer


def test_chat_service_invoke_graph_without_and_with_checkpointer(monkeypatch):
    from app.services import chat_service as module

    service = ChatService.__new__(ChatService)
    graph = FakeGraph(
        {
            "router": lambda state: {"route": "rag"},
            "rag": lambda state: state,
            "payroll": lambda state: state,
            "smalltalk": lambda state: state,
            "finalize": lambda state: state,
        }
    )
    payload = make_payload("Oi")

    monkeypatch.setattr(module, "PostgresSaver", None)
    output = ChatService._invoke_graph(service, graph, payload)
    assert output["question"] == "Oi"

    class FakeSaver:
        def setup(self):
            self.ready = True

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakePostgresSaver:
        @staticmethod
        def from_conn_string(conn_string):
            assert conn_string
            return FakeSaver()

    monkeypatch.setattr(module, "PostgresSaver", FakePostgresSaver)
    output = ChatService._invoke_graph(service, graph, payload)
    assert output["question"] == "Oi"


def test_chat_service_extract_employee_hint():
    assert ChatService._extract_employee_hint("Qual o salario de Ana?") == "Ana"
    assert ChatService._extract_employee_hint("Sem marcador") is None


def test_build_graph_routes_to_expected_nodes():
    graph = build_graph(
        lambda state: {"route": "smalltalk"},
        lambda state: {"answer": "rag", "citations": []},
        lambda state: {"answer": "payroll", "citations": []},
        lambda state: {"answer": "smalltalk", "citations": []},
        lambda state: state,
    )
    compiled = graph.compile()

    result = compiled.invoke({"question": "Oi", "messages": []})

    assert result["route"] == "smalltalk"
    assert result["answer"] == "smalltalk"


def test_vector_repository_methods(monkeypatch):
    from app.repositories.vector_repository import VectorRepository

    executed = []

    class FakeResult:
        def mappings(self):
            return self

        def all(self):
            return [{"chunk_id": 1, "document_id": 2, "title": "Doc", "content": "abc", "distance": 0.1}]

    class FakeDB:
        def scalar(self, stmt):
            return None

        def execute(self, stmt, params=None):
            executed.append((stmt, params))
            return FakeResult()

        def add(self, item):
            executed.append(("add", item))

        def flush(self):
            executed.append(("flush", None))

    repo = VectorRepository(FakeDB())
    assert repo.get_document_by_source_path(1, "x") is None
    assert repo.delete_document_by_source_path(1, "x") is False

    doc = repo.create_document(1, "Doc", "/tmp/doc", "internal")
    chunk = repo.create_chunk(1, 1, 0, "abc", [0.1])
    rows = repo.similarity_search([0.1], [1], top_k=2, search_query="q")

    assert doc.title == "Doc"
    assert chunk.content == "abc"
    assert rows[0]["chunk_id"] == 1
    assert repo.similarity_search([0.1], [], top_k=2) == []


def test_bootstrap_helpers_and_seed_core_data(monkeypatch, tmp_path):
    executed = []

    class FakeConn:
        def execute(self, statement):
            executed.append(str(statement))

    class FakeEngine:
        def begin(self):
            class Ctx:
                def __enter__(self_inner):
                    return FakeConn()

                def __exit__(self_inner, exc_type, exc, tb):
                    return False

            return Ctx()

    bootstrap.ensure_vector_extension(FakeEngine())
    assert "CREATE EXTENSION IF NOT EXISTS vector" in executed[0]

    monkeypatch.setattr(bootstrap, "inspect", lambda engine: SimpleNamespace(get_table_names=lambda: ["a", "b"]))
    bootstrap.verify_tables(object(), ["a"], "db")
    with pytest.raises(RuntimeError):
        bootstrap.verify_tables(object(), ["missing"], "db")

    ingested = []

    class FakeBaseRepository:
        def __init__(self, db):
            self.db = db
            self._bases = db.bases

        def list_all(self):
            return self._bases

        def create(self, payload):
            base = SimpleNamespace(id=1, slug=payload.slug)
            self._bases.append(base)
            return base

    class FakeIngestionService:
        def __init__(self, app_db, vector_db):
            self.parser = SimpleNamespace(list_supported_files=lambda docs_dir: [docs_dir / "a.txt"])

        def ingest_file(self, path, base_id, title, classification, uploaded_by):
            ingested.append((path.name, base_id, title, uploaded_by))

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "a.txt").write_text("a", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "BaseRepository", FakeBaseRepository)
    monkeypatch.setattr(bootstrap, "IngestionService", FakeIngestionService)
    monkeypatch.setattr(bootstrap.settings, "ingestion_source_dir", str(docs_dir))

    app_db = SimpleNamespace(bases=[], flush=lambda: None, commit=lambda: None)
    bootstrap.seed_core_data(app_db, object())
    assert ingested == [("a.txt", 1, "a", "bootstrap")]


def test_bootstrap_databases_calls_expected_steps(monkeypatch):
    calls = []

    monkeypatch.setattr(bootstrap, "create_engine", lambda url, future=True: f"engine:{url}")
    monkeypatch.setattr(bootstrap.AppBase.metadata, "create_all", lambda engine: calls.append(("app_create_all", engine)))
    monkeypatch.setattr(bootstrap.VectorBase.metadata, "create_all", lambda engine: calls.append(("vector_create_all", engine)))
    monkeypatch.setattr(bootstrap, "ensure_vector_extension", lambda engine: calls.append(("ensure_vector_extension", engine)))
    monkeypatch.setattr(bootstrap, "verify_tables", lambda engine, tables, label: calls.append((label, tuple(tables))))

    bootstrap.bootstrap_databases()

    assert ("app_create_all", f"engine:{bootstrap.settings.DB_USERS}") in calls
    assert ("ensure_vector_extension", f"engine:{bootstrap.settings.DB_PGVECTOR}") in calls
