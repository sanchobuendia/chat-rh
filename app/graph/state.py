from typing import Literal, TypedDict
from langgraph.graph.message import add_messages
from typing_extensions import Annotated


class ChatState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    question: str
    route: Literal["rag", "payroll", "smalltalk"]
    answer: str
    citations: list[dict]
