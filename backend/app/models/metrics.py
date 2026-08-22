from sqlalchemy import String, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class FinancialMetric(Base, UUIDPKMixin, TimestampMixin):
    """
    A stored, reproducible snapshot of computed analytics so the audit
    trail and 'what changed and why' explanations (PRD Section 17) have
    something concrete to diff against.
    """
    __tablename__ = "financial_metrics"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    total_income: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_expenses: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    net_cash_flow: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    savings_rate: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    expense_ratio: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    emergency_buffer_months: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
