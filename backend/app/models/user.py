from sqlalchemy import String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class UserType(str, enum.Enum):
    STUDENT = "student"
    MICRO_ENTREPRENEUR = "micro_entrepreneur"


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_type: Mapped[UserType] = mapped_column(SAEnum(UserType), nullable=False, default=UserType.STUDENT)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Data minimization (PRD Section 4.2): only email, name, and a coarse
    # user-type category are collected at signup. Nothing else.

    consents = relationship("Consent", back_populates="user", cascade="all, delete-orphan")
    income_records = relationship("IncomeRecord", back_populates="user", cascade="all, delete-orphan")
    expense_records = relationship("ExpenseRecord", back_populates="user", cascade="all, delete-orphan")
    savings_records = relationship("SavingsRecord", back_populates="user", cascade="all, delete-orphan")
    borrowing_records = relationship("BorrowingRecord", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    credit_scores = relationship("CreditScore", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("AssistantConversation", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
