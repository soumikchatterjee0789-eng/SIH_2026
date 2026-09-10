from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.assistant import AssistantConversation
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantPromptsResponse,
)
from app.utils.response import success_response
from app.utils.deps import get_current_user
from app.services import assistant_service

router = APIRouter(prefix="/api/assistant", tags=["AI Assistant"])


@router.post("/chat")
def chat(payload: AssistantChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = assistant_service.answer_question_detailed(db, user.id, payload.message)

    conversation = AssistantConversation(
        user_id=user.id,
        question=payload.message,
        answer=result["answer"],
        used_insufficient_data_fallback=result["used_insufficient_data_fallback"],
    )
    db.add(conversation)
    db.commit()

    return success_response(
        AssistantChatResponse(
            answer=result["answer"],
            used_insufficient_data_fallback=result["used_insufficient_data_fallback"],
            source=result.get("source", "autonomous_financial_engine"),
            suggested_followups=result.get("suggested_followups", []),
        ).model_dump(mode="json")
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


@router.delete("/history")
def clear_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deleted_count = (
        db.query(AssistantConversation)
        .filter(AssistantConversation.user_id == user.id)
        .delete()
    )
    db.commit()
    return success_response({"cleared": True, "deleted_count": deleted_count})


@router.get("/prompts")
def get_prompts(user: User = Depends(get_current_user)):
    user_type = getattr(user, "user_type", "student")
    prompts = assistant_service.get_suggested_prompts(user_type)
    return success_response(
        AssistantPromptsResponse(user_type=user_type, prompts=prompts).model_dump(mode="json")
    )
