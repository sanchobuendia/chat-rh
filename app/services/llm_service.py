import logging
from functools import lru_cache
from pathlib import Path
from app.services.model_factory import get_chat_model

logger = logging.getLogger(__name__)
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


class LLMService:
    def __init__(self) -> None:
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = get_chat_model()
        return self._model

    def answer(self, question: str, retrieved_chunks: list[dict], structured_result: dict | None = None) -> str:
        prompt = self._build_prompt(question=question, retrieved_chunks=retrieved_chunks, structured_result=structured_result)
        logger.debug(
            "llm_call kind=%s question=%r chunks=%s structured=%s context_preview=%s",
            "structured_answer" if structured_result else "rag_answer",
            question,
            len(retrieved_chunks),
            bool(structured_result),
            self._context_preview(retrieved_chunks),
        )
        response = self.model.invoke(prompt)
        logger.debug(
            "llm_response kind=%s content_preview=%r",
            "structured_answer" if structured_result else "rag_answer",
            self._normalize_content(response)[:300],
        )
        return getattr(response, "content", str(response))

    def decide_route(self, question: str) -> str:
        prompt = self._render_prompt("route_decision.txt", question=question)
        logger.debug("llm_call kind=route_decision question=%r", question)
        response = self.model.invoke(prompt)
        route = self._normalize_content(response).strip().lower()
        logger.debug("llm_response kind=route_decision route_raw=%r", route)
        if route in {"smalltalk", "payroll", "rag"}:
            return route
        return "rag"

    def generate_search_queries(self, question: str, count: int = 3) -> list[str]:
        prompt = self._render_prompt("query_expansion.txt", question=question, count=count)
        logger.debug("llm_call kind=query_expansion question=%r count=%s", question, count)
        response = self.model.invoke(prompt)
        content = self._normalize_content(response)
        queries = [line.strip("-* \t") for line in content.splitlines() if line.strip()]
        normalized_queries: list[str] = []
        for query in queries:
            if query and query not in normalized_queries:
                normalized_queries.append(query)
        if question not in normalized_queries:
            normalized_queries.insert(0, question)
        expanded = normalized_queries[:count]
        while len(expanded) < count:
            expanded.append(question)
        logger.debug("llm_response kind=query_expansion queries=%s", expanded)
        return expanded

    def converse(self, question: str, user_name: str | None = None) -> str:
        prompt = self._render_prompt(
            "smalltalk.txt",
            question=question,
            greeting_name=f" para {user_name}" if user_name else "",
        )
        logger.debug("llm_call kind=smalltalk question=%r user_name=%r", question, user_name)
        response = self.model.invoke(prompt)
        logger.debug("llm_response kind=smalltalk content_preview=%r", self._normalize_content(response)[:300])
        return getattr(response, "content", str(response))

    @staticmethod
    @lru_cache(maxsize=None)
    def _load_prompt(prompt_name: str) -> str:
        return (PROMPTS_DIR / prompt_name).read_text(encoding="utf-8")

    def _render_prompt(self, prompt_name: str, **kwargs) -> str:
        return self._load_prompt(prompt_name).format(**kwargs)

    @staticmethod
    def _normalize_content(response) -> str:
        content = getattr(response, "content", str(response))
        if isinstance(content, list):
            return " ".join(str(item) for item in content)
        return str(content)

    @staticmethod
    def _context_preview(retrieved_chunks: list[dict]) -> list[dict]:
        preview: list[dict] = []
        for item in retrieved_chunks:
            preview.append(
                {
                    "title": item.get("title"),
                    "chunk_id": item.get("chunk_id"),
                    "snippet": item.get("content", "")[:180],
                }
            )
        return preview

    @staticmethod
    def _build_prompt(question: str, retrieved_chunks: list[dict], structured_result: dict | None = None) -> str:
        if structured_result:
            return LLMService._load_prompt("structured_answer.txt").format(
                question=question,
                structured_result=structured_result,
            )

        if not retrieved_chunks:
            return LLMService._load_prompt("no_context_answer.txt").format(question=question)

        context = "\n\n".join(
            f"[Documento: {item['title']} | Chunk: {item['chunk_id']}]\n{item['content']}"
            for item in retrieved_chunks
        )
        return LLMService._load_prompt("rag_answer.txt").format(question=question, context=context)
