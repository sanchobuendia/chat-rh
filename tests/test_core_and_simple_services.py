import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core import config as config_module
from app.core.logging import configure_logging
from app.schemas.base import BaseCreate, BaseRead, GrantAccessRequest, RevokeAccessRequest
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.schemas.ingestion import IngestionJobRead
from app.schemas.payroll import PayrollLookupResponse
from app.schemas.user import UserCreate, UserRead
from app.services.chunker_service import ChunkerService
from app.services.document_parser import DocumentParser
from app.services.embedding_service import EmbeddingService
from app.services.model_factory import get_chat_model
from app.services.router_service import RouterService


def test_get_settings_uses_env_and_cache(monkeypatch):
    config_module.get_settings.cache_clear()
    monkeypatch.setenv("APP_NAME", "chat-rh-test")
    monkeypatch.setenv("DB_USERS", "sqlite:///users.db")
    monkeypatch.setenv("DB_HISTORY", "postgresql://history")
    monkeypatch.setenv("DB_PGVECTOR", "sqlite:///vector.db")

    settings = config_module.get_settings()
    cached = config_module.get_settings()

    assert settings.app_name == "chat-rh-test"
    assert settings.DB_USERS == "sqlite:///users.db"
    assert settings.embedding_model == "intfloat/multilingual-e5-small"
    assert cached is settings


def test_configure_logging_uses_uppercase_level(monkeypatch):
    calls = {}

    def fake_basic_config(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    configure_logging("debug")

    assert calls["level"] == logging.DEBUG
    assert "[%(name)s]" in calls["format"]


def test_chunker_service_splits_and_preserves_overlap():
    chunks = ChunkerService().split("abcdefghij", chunk_size=4, overlap=1)

    assert chunks == ["abcd", "defg", "ghij"]


def test_chunker_service_returns_single_chunk_for_short_text():
    assert ChunkerService().split("  hello   world  ", chunk_size=50) == ["hello world"]


def test_document_parser_reads_text_and_lists_supported_files(tmp_path):
    parser = DocumentParser()
    txt = tmp_path / "a.txt"
    txt.write_text("hello", encoding="utf-8")
    md = tmp_path / "b.md"
    md.write_text("world", encoding="utf-8")
    unsupported = tmp_path / "c.json"
    unsupported.write_text("{}", encoding="utf-8")

    assert parser.parse(txt) == "hello"
    assert parser.list_supported_files(tmp_path) == [txt, md]


def test_document_parser_rejects_unsupported_extension(tmp_path):
    file_path = tmp_path / "a.json"
    file_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        DocumentParser().parse(file_path)


def test_document_parser_parses_pdf_and_docx(monkeypatch, tmp_path):
    pdf_path = tmp_path / "a.pdf"
    docx_path = tmp_path / "a.docx"
    pdf_path.write_bytes(b"%PDF")
    docx_path.write_bytes(b"PK")

    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakeReader:
        def __init__(self, path):
            assert str(path).endswith(".pdf")
            self.pages = [FakePage(" first "), FakePage(""), FakePage("second")]

    class FakeDocument:
        def __init__(self, path):
            assert str(path).endswith(".docx")
            self.paragraphs = [SimpleNamespace(text=" one "), SimpleNamespace(text=""), SimpleNamespace(text="two")]

    monkeypatch.setattr("app.services.document_parser.PdfReader", FakeReader)
    monkeypatch.setattr("app.services.document_parser.DocxDocument", FakeDocument)

    assert DocumentParser().parse(pdf_path) == "first\n\nsecond"
    assert DocumentParser().parse(docx_path) == "one\ntwo"


def test_router_service_delegates_to_llm():
    llm = SimpleNamespace(decide_route=lambda question: "smalltalk")

    assert RouterService(llm).route("Oi") == "smalltalk"


def test_embedding_service_uses_local_sentence_transformer(monkeypatch):
    from app.services import embedding_service as module

    module.get_embedder.cache_clear()
    monkeypatch.setattr(module.settings, "embedding_provider", "local")
    monkeypatch.setattr(module.settings, "embedding_model", "intfloat/multilingual-e5-small")

    class FakeVector:
        def tolist(self):
            return [0.5, 0.5, 0.5, 0.5]

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            assert model_name == "intfloat/multilingual-e5-small"

        def encode(self, text, normalize_embeddings):
            assert text == "hello"
            assert normalize_embeddings is True
            return FakeVector()

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeSentenceTransformer)

    vector = EmbeddingService().embed("hello")

    assert len(vector) == 4
    assert vector == [0.5, 0.5, 0.5, 0.5]


def test_embedding_service_reuses_cached_embedder(monkeypatch):
    from app.services import embedding_service as module

    module.get_embedder.cache_clear()
    monkeypatch.setattr(module.settings, "embedding_provider", "local")
    monkeypatch.setattr(module.settings, "embedding_model", "intfloat/multilingual-e5-small")
    calls = {"count": 0}

    class FakeVector:
        def tolist(self):
            return [0.1, 0.2]

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            calls["count"] += 1

        def encode(self, text, normalize_embeddings):
            return FakeVector()

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeSentenceTransformer)

    first = EmbeddingService().embed("hello")
    second = EmbeddingService().embed("world")

    assert first == [0.1, 0.2]
    assert second == [0.1, 0.2]
    assert calls["count"] == 1


def test_embedding_service_uses_openai_embedder(monkeypatch):
    from app.services import embedding_service as module

    module.get_embedder.cache_clear()
    class FakeOpenAIEmbeddings:
        def __init__(self, model):
            self.model = model

        def embed_query(self, text):
            return [0.1, 0.2, 0.3]

    monkeypatch.setattr(module.settings, "embedding_provider", "openai")
    monkeypatch.setattr(module.settings, "embedding_model", "text-embedding-3-small")
    monkeypatch.setattr("langchain_openai.OpenAIEmbeddings", FakeOpenAIEmbeddings)

    assert EmbeddingService().embed("hello") == [0.1, 0.2, 0.3]


def test_embedding_service_uses_bedrock_embedder(monkeypatch):
    from app.services import embedding_service as module

    module.get_embedder.cache_clear()
    class FakeBedrockEmbeddings:
        def __init__(self, model_id):
            self.model_id = model_id

        def embed_query(self, text):
            return [0.4, 0.5]

    monkeypatch.setattr(module.settings, "embedding_provider", "bedrock")
    monkeypatch.setattr(module.settings, "BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    monkeypatch.setattr("langchain_aws.BedrockEmbeddings", FakeBedrockEmbeddings)

    assert EmbeddingService().embed("hello") == [0.4, 0.5]


def test_embedding_service_rejects_unknown_provider(monkeypatch):
    from app.services import embedding_service as module

    module.get_embedder.cache_clear()
    monkeypatch.setattr(module.settings, "embedding_provider", "unknown")

    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        EmbeddingService().embed("hello")


def test_model_factory_initializes_chat_model(monkeypatch):
    from app.services import model_factory as module

    calls = {}

    def fake_init_chat_model(model_name, model_provider, temperature):
        calls["model_name"] = model_name
        calls["model_provider"] = model_provider
        calls["temperature"] = temperature
        return "chat-model"

    monkeypatch.setattr(module, "init_chat_model", fake_init_chat_model)
    monkeypatch.setattr(module.settings, "MODEL_PROVIDER", " provider ")
    monkeypatch.setattr(module.settings, "BEDROCK_MODEL_ID", " model ")
    monkeypatch.setattr(module.settings, "MODEL_TEMPERATURE", 0.4)

    assert get_chat_model() == "chat-model"
    assert calls == {
        "model_name": "model",
        "model_provider": "provider",
        "temperature": 0.4,
    }


@pytest.mark.parametrize(
    ("provider", "model_name", "message"),
    [
        ("", "model", "MODEL_PROVIDER is not configured"),
        ("provider", "", "MODEL_NAME is not configured"),
    ],
)
def test_model_factory_validates_required_settings(monkeypatch, provider, model_name, message):
    from app.services import model_factory as module

    monkeypatch.setattr(module.settings, "MODEL_PROVIDER", provider)
    monkeypatch.setattr(module.settings, "BEDROCK_MODEL_ID", model_name)

    with pytest.raises(ValueError, match=message):
        module.get_chat_model()


def test_schema_models_validate_from_attributes():
    base = BaseRead.model_validate(
        SimpleNamespace(id=1, name="RH", slug="rh", description=None, classification="internal", is_active=True)
    )
    user = UserRead.model_validate(
        SimpleNamespace(
            id=1,
            email="user@example.com",
            full_name="User Name",
            role="employee",
            department="general",
            is_manager=False,
            is_active=True,
        )
    )
    ingestion = IngestionJobRead.model_validate(
        SimpleNamespace(
            id=1,
            file_name="file.txt",
            title="File",
            base_id=1,
            classification="internal",
            status="completed",
            uploaded_by="tester",
        )
    )

    assert BaseCreate(name="RH", slug="rh").classification == "internal"
    assert GrantAccessRequest(email="user@example.com", slug="rh").slug == "rh"
    assert RevokeAccessRequest(email="user@example.com", slug="rh").email == "user@example.com"
    assert UserCreate(email="user@example.com", full_name="User").role == "employee"
    assert ChatRequest().thread_id == "test01"
    citation = Citation(document_id=1, title="Doc", chunk_id=2, snippet="a", distance=0.12, score=0.88)
    assert citation.chunk_id == 2
    assert citation.score == 0.88
    assert ChatResponse(answer="ok", route="rag", citations=[]).answer == "ok"
    assert PayrollLookupResponse(
        employee_name="Ana",
        document_number_masked="***.***.***-00",
        department="RH",
        role_title="Analista",
        monthly_salary=1000.0,
        currency="BRL",
    ).currency == "BRL"
    assert base.slug == "rh"
    assert user.email == "user@example.com"
    assert ingestion.file_name == "file.txt"
