from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class Recommendation(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "recommendations"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)  # savings | expenses | borrowing
    message: Mapped[str] = mapped_column(Text, nullable=False)
    basis: Mapped[str] = mapped_column(Text, nullable=False)  # the underlying metric/data it's based on

    user = relationship("User", back_populates="recommendations")
