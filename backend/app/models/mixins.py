"""
Shared mixins for all ORM models.

PRD Section 33 requires stable unique IDs (user_id, transaction_id,
consent_id, score_id, ...). We use UUID strings everywhere for that
reason - they are stable, non-guessable, and safe to expose via API
without leaking row counts.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPKMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
