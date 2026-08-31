from datetime import datetime

from sqlalchemy import String, ForeignKey, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class Consent(Base, UUIDPKMixin, TimestampMixin):
    """
    Tracks explicit, revocable, purpose-limited consent per data category
    (PRD Section 4.1 - Consent First / Section 8 - Consent Dashboard).

    Records: what data, why it was requested, when consent was given,
    what purpose was accepted, and whether it is still active.
    """
    __tablename__ = "consents"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # e.g. "income", "expenses", "transactions", "savings", "borrowing"
    data_category: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(String(255), nullable=False)

    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="consents")

    __table_args__ = (
        # Speeds up grant_consent()'s "find existing row for this category" lookup.
        Index("ix_consents_user_category", "user_id", "data_category"),
        # Speeds up get_active_consent_categories(), which every analytics /
        # credit-readiness / recommendation call runs at least once.
        Index("ix_consents_user_active", "user_id", "is_active"),
    )
