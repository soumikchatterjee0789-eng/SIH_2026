from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.credit import CreditReadinessOut, ScoreFactorOut
from app.utils.response import success_response
from app.utils.errors import APIError, ErrorCode
from app.utils.deps import get_current_user, require_consent
from app.services import credit_readiness_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/credit-readiness", tags=["Credit Readiness"])


@router.get("")
def get_credit_readiness(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("income")),
):
    """
    Always recomputes live from current consented data (PRD Section 4
    point 6: 'Recalculable whenever the underlying data changes') and
    persists the result as the new current score, so history + audit
    trail stay accurate.
    """
    previous = credit_readiness_service.get_current_score(db, user.id)

    try:
        result = credit_readiness_service.calculate_credit_readiness(db, user.id)
    except credit_readiness_service.InsufficientDataError as e:
        raise APIError(200, str(e), ErrorCode.INSUFFICIENT_DATA)

    saved = credit_readiness_service.save_credit_score(db, user.id, result)

    action = "SCORE_RECALCULATED" if previous else "SCORE_GENERATED"
    log_action(
        db, user.id, action, "credit_score",
        old_value=str(previous.score) if previous else None,
        new_value=str(saved.score),
    )

    out = CreditReadinessOut(
        score=saved.score,
        rating=saved.rating,
        disclaimer=saved.disclaimer,
        factors=[ScoreFactorOut.model_validate(f) for f in saved.factors],
        calculated_at=saved.created_at,
    )
    return success_response(out.model_dump(mode="json"))


@router.get("/explanation")
def get_credit_readiness_explanation(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _consent=Depends(require_consent("income")),
):
    """Returns only the factor breakdown for the CURRENT stored score,
    without triggering a recalculation - useful for a lightweight
    'why' panel in the UI."""
    current = credit_readiness_service.get_current_score(db, user.id)
    if current is None:
        raise APIError(
            200,
            "Credit readiness cannot be calculated yet because more consented financial information is required.",
            ErrorCode.INSUFFICIENT_DATA,
        )

    out = CreditReadinessOut(
        score=current.score,
        rating=current.rating,
        disclaimer=current.disclaimer,
        factors=[ScoreFactorOut.model_validate(f) for f in current.factors],
        calculated_at=current.created_at,
    )
    return success_response(out.model_dump(mode="json"))
