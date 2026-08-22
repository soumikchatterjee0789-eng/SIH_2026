from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, UserOut, TokenOut
from app.utils.response import success_response
from app.utils.errors import APIError, ErrorCode
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.deps import get_current_user
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register")
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise APIError(409, "An account with this email already exists.", ErrorCode.ALREADY_EXISTS)

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        user_type=payload.user_type,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(db, user.id, "USER_REGISTERED", "user", new_value=user.email)

    token = create_access_token(subject=user.id)
    return success_response(
        TokenOut(access_token=token, user=UserOut.model_validate(user)).model_dump(mode="json"),
        message="Account created successfully.",
    )


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Uses OAuth2PasswordRequestForm (username/password form fields) so this
    endpoint is directly compatible with FastAPI's Swagger UI "Authorize"
    button and standard OAuth2 client libraries. `username` = email.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise APIError(401, "Incorrect email or password.", ErrorCode.UNAUTHORIZED)

    token = create_access_token(subject=user.id)
    return success_response(
        TokenOut(access_token=token, user=UserOut.model_validate(user)).model_dump(mode="json"),
        message="Login successful.",
    )


@router.post("/login-json")
def login_json(payload: UserLogin, db: Session = Depends(get_db)):
    """JSON-friendly login alternative for frontend clients that don't want
    to send an x-www-form-urlencoded body."""
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise APIError(401, "Incorrect email or password.", ErrorCode.UNAUTHORIZED)

    token = create_access_token(subject=user.id)
    return success_response(
        TokenOut(access_token=token, user=UserOut.model_validate(user)).model_dump(mode="json"),
        message="Login successful.",
    )


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    # JWTs are stateless; logout is handled client-side by discarding the
    # token. This endpoint exists for API-contract completeness and to
    # give the frontend a clean, documented action to call.
    return success_response(None, message="Logged out successfully.")
