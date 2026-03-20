from types import SimpleNamespace

from app.services.llm_service import LLMService


class FakeModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return self.responses.pop(0)


def test_llm_service_model_is_cached(monkeypatch):
    calls = {"count": 0}

    def fake_get_chat_model():
        calls["count"] += 1
        return "model"

    monkeypatch.setattr("app.services.llm_service.get_chat_model", fake_get_chat_model)

    service = LLMService()

    assert service.model == "model"
    assert service.model == "model"
    assert calls["count"] == 1


def test_llm_service_answer_uses_prompt_and_returns_content(monkeypatch):
    service = LLMService()
    service._model = FakeModel([SimpleNamespace(content="final answer")])
    monkeypatch.setattr(service, "_build_prompt", lambda **kwargs: "PROMPT")

    answer = service.answer("Pergunta", [{"title": "Doc", "chunk_id": 1, "content": "Context"}])

    assert answer == "final answer"
    assert service.model.prompts == ["PROMPT"]


def test_llm_service_decide_route_falls_back_to_rag(monkeypatch):
    service = LLMService()
    service._model = FakeModel([SimpleNamespace(content="unknown"), SimpleNamespace(content="Payroll ")])
    monkeypatch.setattr(service, "_render_prompt", lambda *args, **kwargs: "ROUTE")

    assert service.decide_route("Oi") == "rag"
    assert service.decide_route("Salario") == "payroll"


def test_llm_service_generate_search_queries_deduplicates_and_pads(monkeypatch):
    service = LLMService()
    service._model = FakeModel([SimpleNamespace(content="- consulta 1\n- consulta 1\nconsulta 2")])
    monkeypatch.setattr(service, "_render_prompt", lambda *args, **kwargs: "EXPAND")

    queries = service.generate_search_queries("consulta original", count=4)

    assert queries == ["consulta original", "consulta 1", "consulta 2", "consulta original"]


def test_llm_service_converse_uses_name(monkeypatch):
    service = LLMService()
    service._model = FakeModel([SimpleNamespace(content="ola")])
    monkeypatch.setattr(service, "_render_prompt", lambda *args, **kwargs: "SMALLTALK")

    assert service.converse("Oi", user_name="Ana") == "ola"
    assert service.model.prompts == ["SMALLTALK"]


def test_llm_service_helpers_normalize_preview_and_build_prompt(monkeypatch):
    monkeypatch.setattr(
        LLMService,
        "_load_prompt",
        staticmethod(
            lambda prompt_name: {
                "structured_answer.txt": "STRUCT {question} {structured_result}",
                "no_context_answer.txt": "NOCTX {question}",
                "rag_answer.txt": "RAG {question} {context}",
            }[prompt_name]
        ),
    )

    normalized = LLMService._normalize_content(SimpleNamespace(content=["a", 2]))
    preview = LLMService._context_preview([{"title": "Doc", "chunk_id": 7, "content": "x" * 200}])
    structured = LLMService._build_prompt("Pergunta", [], {"salary": 10})
    no_context = LLMService._build_prompt("Pergunta", [])
    rag = LLMService._build_prompt(
        "Pergunta",
        [{"title": "Doc", "chunk_id": 1, "content": "Trecho"}],
    )

    assert normalized == "a 2"
    assert preview == [{"title": "Doc", "chunk_id": 7, "snippet": "x" * 180}]
    assert structured == "STRUCT Pergunta {'salary': 10}"
    assert no_context == "NOCTX Pergunta"
    assert "[Documento: Doc | Chunk: 1]" in rag
