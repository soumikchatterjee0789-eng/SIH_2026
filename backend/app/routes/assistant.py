from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.assistant import AssistantConversation
from app.schemas.assistant import AssistantChatRequest, AssistantChatResponse
from app.utils.response import success_response
from app.utils.deps import get_current_user
from app.services import assistant_service

router = APIRouter(prefix="/api/assistant", tags=["AI Assistant"])


@router.post("/chat")
def chat(payload: AssistantChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    answer, used_fallback = assistant_service.answer_question(db, user.id, payload.message)

    conversation = AssistantConversation(
        user_id=user.id,
        question=payload.message,
        answer=answer,
        used_insufficient_data_fallback=used_fallback,
    )
    db.add(conversation)
    db.commit()

    return success_response(
        AssistantChatResponse(answer=answer, used_insufficient_data_fallback=used_fallback).model_dump(mode="json")
    )


@router.get("/history")
def get_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversations = (
        db.query(AssistantConversation)
        .filter(AssistantConversation.user_id == user.id)
        .order_by(AssistantConversation.created_at.desc())
        .limit(50)
        .all()
    )
    return success_response(
        [
            {"question": c.question, "answer": c.answer, "created_at": c.created_at.isoformat()}
            for c in conversations
        ]
    )
