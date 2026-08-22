from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class AuditLog(Base, UUIDPKMixin, TimestampMixin):
    """
    Tracks important actions per PRD Section 24: data created/updated/
    deleted, consent granted/revoked, score generated/recalculated, and
    user corrections. Not exposed in the normal dashboard.
    """
    __tablename__ = "audit_logs"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="audit_logs")
