from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str = Field(default="test01", description="Conversation thread id")
    question: str = Field(default="Olá", description="User's question")
    top_k: int = 3


class Citation(BaseModel):
    document_id: int
    title: str
    chunk_id: int
    snippet: str
    distance: float | None = None
    score: float | None = None


class ChatResponse(BaseModel):
    answer: str
    route: str
    citations: list[Citation]
