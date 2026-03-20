import logging
from typing import Any
from app.core.config import get_settings
from app.graph.builder import build_graph
from app.repositories.audit_repository import AuditRepository
from app.schemas.auth import AuthContext
from app.schemas.chat import ChatRequest, ChatResponse, Citation
from app.services.llm_service import LLMService
from app.services.payroll_service import PayrollService
from app.services.retrieval_service import RetrievalService
from app.services.router_service import RouterService

settings = get_settings()
logger = logging.getLogger(__name__)

try:
    from langgraph.checkpoint.postgres import PostgresSaver
except Exception:
    PostgresSaver = None


class ChatService:
    def __init__(self, app_db, vector_db):
        self.app_db = app_db
        self.vector_db = vector_db
        self.audit = AuditRepository(app_db)
        self.llm_service = LLMService()
        self.router_service = RouterService(self.llm_service)
        self.retrieval_service = RetrievalService(app_db, vector_db, self.llm_service)
        self.payroll_service = PayrollService(app_db)

    def run(self, payload: ChatRequest, user: AuthContext) -> ChatResponse:
        requested_employee = self._extract_employee_hint(payload.question)
        logger.debug(
            "chat_request user_id=%s email=%s thread_id=%s question=%r",
            user.user_id,
            user.email,
            payload.thread_id,
            payload.question,
        )

        def router_node(state: dict[str, Any]) -> dict[str, Any]:
            route = self.router_service.route(state["question"])
            logger.debug("chat_route_decision thread_id=%s route=%s", payload.thread_id, route)
            return {"route": route}

        def smalltalk_node(state: dict[str, Any]) -> dict[str, Any]:
            logger.debug("agent_tool_use thread_id=%s tool=smalltalk_node", payload.thread_id)
            return {
                "answer": self.llm_service.converse(
                    question=state["question"],
                    user_name=user.full_name.split()[0] if user.full_name else None,
                ),
                "citations": [],
            }

        def rag_node(state: dict[str, Any]) -> dict[str, Any]:
            logger.debug("agent_tool_use thread_id=%s tool=rag_node top_k=%s", payload.thread_id, payload.top_k)
            results = self.retrieval_service.search(user=user, question=state["question"], top_k=payload.top_k)
            logger.debug(
                "rag_results user_id=%s thread_id=%s count=%s chunks=%s",
                user.user_id,
                payload.thread_id,
                len(results),
                [
                    {
                        "title": item["title"],
                        "chunk_id": item["chunk_id"],
                        "snippet": item["content"][:180],
                    }
                    for item in results
                ],
            )
            answer = self.llm_service.answer(question=state["question"], retrieved_chunks=results)
            citations = [
                {
                    "document_id": item["document_id"],
                    "title": item["title"],
                    "chunk_id": item["chunk_id"],
                    "snippet": item["content"][:180],
                    "distance": item.get("distance"),
                    "score": item.get("score"),
                }
                for item in results
            ]
            return {"answer": answer, "citations": citations}

        def payroll_node(state: dict[str, Any]) -> dict[str, Any]:
            logger.debug(
                "agent_tool_use thread_id=%s tool=payroll_node requested_employee=%r",
                payload.thread_id,
                requested_employee,
            )
            if not requested_employee:
                return {"answer": "Informe o nome do colaborador para consulta estruturada de salário.", "citations": []}
            result = self.payroll_service.lookup_employee(employee_name=requested_employee, requester=user)
            if not result:
                return {"answer": "Não encontrei o colaborador ou você não tem acesso a essa consulta.", "citations": []}
            answer = self.llm_service.answer(question=state["question"], retrieved_chunks=[], structured_result=result.model_dump())
            return {"answer": answer, "citations": []}

        def finalize_node(state: dict[str, Any]) -> dict[str, Any]:
            return state

        graph = build_graph(router_node, rag_node, payroll_node, smalltalk_node, finalize_node)
        output = self._invoke_graph(
            graph=graph,
            payload=payload,
        )
        logger.debug(
            "chat_response thread_id=%s route=%s citations=%s answer_preview=%r",
            payload.thread_id,
            output.get("route", "rag"),
            len(output.get("citations", [])),
            output.get("answer", "")[:200],
        )
        self.audit.log(user.email, "chat", payload.question, output.get("answer"))
        self.app_db.commit()
        return ChatResponse(
            answer=output.get("answer", ""),
            route=output.get("route", "rag"),
            citations=[Citation(**c) for c in output.get("citations", [])],
        )

    def _invoke_graph(self, graph, payload: ChatRequest) -> dict[str, Any]:
        request_input = {"question": payload.question, "messages": []}
        request_config = {"configurable": {"thread_id": payload.thread_id}}

        if PostgresSaver:
            with PostgresSaver.from_conn_string(settings.DB_HISTORY) as checkpointer:
                checkpointer.setup()
                compiled = graph.compile(checkpointer=checkpointer)
                return compiled.invoke(request_input, config=request_config)

        compiled = graph.compile()
        return compiled.invoke(request_input, config=request_config)

    @staticmethod
    def _extract_employee_hint(question: str) -> str | None:
        marker = "de "
        lowered = question.lower()
        if marker in lowered:
            idx = lowered.rfind(marker)
            return question[idx + len(marker):].strip().strip("?.")
        return None
