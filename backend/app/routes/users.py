from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate
from app.utils.response import success_response
from app.utils.deps import get_current_user
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return success_response(UserOut.model_validate(user).model_dump(mode="json"))


@router.put("/me")
def update_me(payload: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    old_values = {"full_name": user.full_name, "user_type": user.user_type.value}

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.user_type is not None:
        user.user_type = payload.user_type

    db.commit()
    db.refresh(user)

    log_action(
        db,
        user.id,
        "USER_UPDATED",
        "user_profile",
        old_value=str(old_values),
        new_value=str({"full_name": user.full_name, "user_type": user.user_type.value}),
    )

    return success_response(UserOut.model_validate(user).model_dump(mode="json"), message="Profile updated.")
