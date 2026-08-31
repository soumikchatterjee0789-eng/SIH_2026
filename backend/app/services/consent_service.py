from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.consent import Consent
from app.config.thresholds import CONSENT_CATEGORIES
from app.utils.errors import APIError, ErrorCode
from app.services.audit_service import log_action


def list_consents(db: Session, user_id: str) -> list[Consent]:
    return db.query(Consent).filter(Consent.user_id == user_id).order_by(Consent.created_at.desc()).all()


def grant_consent(db: Session, user_id: str, data_category: str, purpose: str | None) -> Consent:
    if data_category not in CONSENT_CATEGORIES:
        raise APIError(
            400,
            f"'{data_category}' is not a recognized data category. Valid categories: "
            f"{', '.join(CONSENT_CATEGORIES.keys())}.",
            ErrorCode.INVALID_INPUT,
        )

    resolved_purpose = purpose or CONSENT_CATEGORIES[data_category]

    # Re-activate an existing consent record for this category if present,
    # otherwise create a new one - keeps a clean one-active-per-category model.
    existing = (
        db.query(Consent)
        .filter(Consent.user_id == user_id, Consent.data_category == data_category)
        .order_by(Consent.created_at.desc())
        .first()
    )

    now = datetime.now(timezone.utc)

    if existing and not existing.is_active:
        existing.is_active = True
        existing.granted_at = now
        existing.revoked_at = None
        existing.purpose = resolved_purpose
        db.commit()
        db.refresh(existing)
        log_action(db, user_id, "CONSENT_GRANTED", data_category, new_value=resolved_purpose)
        return existing

    if existing and existing.is_active:
        return existing  # already active, idempotent

    consent = Consent(
        user_id=user_id,
        data_category=data_category,
        purpose=resolved_purpose,
        granted_at=now,
        is_active=True,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    log_action(db, user_id, "CONSENT_GRANTED", data_category, new_value=resolved_purpose)
    return consent


def get_active_consent_categories(db: Session, user_id: str) -> set[str]:
    """
    Returns the set of data categories the user currently has ACTIVE
    consent for. Used everywhere financial data is aggregated (analytics,
    credit readiness, recommendations) so that revoking consent for a
    category immediately stops that category's data from being counted -
    without requiring the underlying records to be deleted (PRD: "Revoking
    consent immediately blocks further use").
    """
    rows = (
        db.query(Consent.data_category)
        .filter(Consent.user_id == user_id, Consent.is_active.is_(True))
        .all()
    )
    return {row[0] for row in rows}


def revoke_consent(db: Session, user_id: str, consent_id: str) -> Consent:
    consent = db.query(Consent).filter(Consent.id == consent_id, Consent.user_id == user_id).first()
    if consent is None:
        raise APIError(404, "Consent record not found.", ErrorCode.DATA_NOT_FOUND)

    consent.is_active = False
    consent.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(consent)
    log_action(db, user_id, "CONSENT_REVOKED", consent.data_category, old_value="active", new_value="revoked")
    return consent
