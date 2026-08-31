from datetime import date

from sqlalchemy import String, ForeignKey, Numeric, Date, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class FinancialProfile(Base, UUIDPKMixin, TimestampMixin):
    """One-to-one supplemental profile info for a user (non-sensitive only)."""
    __tablename__ = "financial_profiles"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    current_savings: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    emergency_savings: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    monthly_savings_target: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)


class IncomeRecord(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "income_records"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(String(32), nullable=False)  # monthly | weekly | one_time | irregular
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="income_records")

    __table_args__ = (Index("ix_income_records_user_date", "user_id", "record_date"),)


class ExpenseRecord(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "expense_records"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="expense_records")

    __table_args__ = (Index("ix_expense_records_user_date", "user_id", "record_date"),)


class SavingsRecord(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "savings_records"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    current_savings: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    monthly_savings: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    emergency_savings: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)

    user = relationship("User", back_populates="savings_records")

    # get_latest_savings_snapshot() always orders by (record_date desc,
    # created_at desc) - this index lets that be an index scan, not a sort.
    __table_args__ = (Index("ix_savings_records_user_date", "user_id", "record_date", "created_at"),)


class BorrowingRecord(Base, UUIDPKMixin, TimestampMixin):
    """Optional - only created if the user consents to sharing it (PRD Section 9)."""
    __tablename__ = "borrowing_records"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    existing_loan_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    monthly_repayment: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    remaining_period_months: Mapped[int] = mapped_column(default=0)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)

    user = relationship("User", back_populates="borrowing_records")

    __table_args__ = (Index("ix_borrowing_records_user_date", "user_id", "record_date"),)
