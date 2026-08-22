from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class AssistantConversation(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "assistant_conversations"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    used_insufficient_data_fallback: Mapped[bool] = mapped_column(default=False)

    user = relationship("User", back_populates="conversations")
