"""
Reusable FastAPI dependencies:
  - get_current_user: enforces authentication on protected routes.
  - require_consent(category): enforces that the user has an ACTIVE,
    non-revoked consent for a given data category before any related
    data is read/written/used in calculations (PRD Section 4.1).
"""
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.consent import Consent
from app.utils.security import decode_access_token
from app.utils.errors import APIError, ErrorCode

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if not token:
        raise APIError(401, "Authentication required.", ErrorCode.UNAUTHORIZED)

    user_id = decode_access_token(token)
    if not user_id:
        raise APIError(401, "Invalid or expired session. Please log in again.", ErrorCode.UNAUTHORIZED)

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise APIError(401, "Invalid or expired session. Please log in again.", ErrorCode.UNAUTHORIZED)

    return user


def require_consent(category: str):
    """
    Returns a FastAPI dependency that raises CONSENT_REQUIRED /
    CONSENT_REVOKED if the current user has not granted (or has revoked)
    consent for the given data category.

    Usage:
        @router.post("/api/financial-data")
        def add_income(..., user: User = Depends(get_current_user),
                        _consent = Depends(require_consent("income"))):
    """

    def dependency(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        consent = (
            db.query(Consent)
            .filter(Consent.user_id == user.id, Consent.data_category == category)
            .order_by(Consent.created_at.desc())
            .first()
        )
        if consent is None:
            raise APIError(
                403,
                f"Consent for '{category}' data is required before this action can be performed.",
                ErrorCode.CONSENT_REQUIRED,
            )
        if not consent.is_active:
            raise APIError(
                403,
                f"Consent for '{category}' data was revoked, so this action cannot be performed.",
                ErrorCode.CONSENT_REVOKED,
            )
        return consent

    return dependency
