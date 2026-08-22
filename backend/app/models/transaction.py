from datetime import date

from sqlalchemy import String, ForeignKey, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class Transaction(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "transactions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # income | expense
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="Other")
    is_corrected: Mapped[bool] = mapped_column(default=False)
    source_batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # groups a CSV upload

    user = relationship("User", back_populates="transactions")
