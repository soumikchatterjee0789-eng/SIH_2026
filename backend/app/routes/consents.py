from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.consent import ConsentCreate, ConsentOut
from app.utils.response import success_response
from app.utils.deps import get_current_user
from app.services import consent_service

router = APIRouter(prefix="/api/consents", tags=["Consent"])


@router.get("")
def get_consents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    consents = consent_service.list_consents(db, user.id)
    return success_response([ConsentOut.model_validate(c).model_dump(mode="json") for c in consents])


@router.post("")
def create_consent(payload: ConsentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    consent = consent_service.grant_consent(db, user.id, payload.data_category, payload.purpose)
    return success_response(
        ConsentOut.model_validate(consent).model_dump(mode="json"), message="Consent granted."
    )


@router.delete("/{consent_id}")
def revoke_consent(consent_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    consent = consent_service.revoke_consent(db, user.id, consent_id)
    return success_response(
        ConsentOut.model_validate(consent).model_dump(mode="json"), message="Consent revoked."
    )
