from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_app_db, get_vector_db
from app.schemas.auth import AuthContext
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user: AuthContext = Depends(get_current_user),
    app_db: Session = Depends(get_app_db),
    vector_db: Session = Depends(get_vector_db),
) -> ChatResponse:
    service = ChatService(app_db=app_db, vector_db=vector_db)
    return service.run(payload, user)
