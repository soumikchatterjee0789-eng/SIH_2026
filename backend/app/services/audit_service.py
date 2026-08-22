"""
Audit trail service (PRD Section 24).

Every important mutation (data create/update/delete, consent grant/revoke,
score generation/recalculation, user correction) should call log_action().
"""
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def log_action(
    db: Session,
    user_id: str,
    action: str,
    data_type: str,
    old_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        data_type=data_type,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
