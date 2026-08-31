from sqlalchemy import String, ForeignKey, Numeric, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class CreditScore(Base, UUIDPKMixin, TimestampMixin):
    """
    The platform's own explainable Credit Readiness Score.

    IMPORTANT (PRD Section 4.5 - Score Separation): this is never a bureau
    credit score, and every API/UI surface must label it accordingly.
    """
    __tablename__ = "credit_scores"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    score: Mapped[int] = mapped_column(nullable=False)  # 0-100
    rating: Mapped[str] = mapped_column(String(32), nullable=False)
    is_current: Mapped[bool] = mapped_column(default=True)
    disclaimer: Mapped[str] = mapped_column(
        Text,
        default=(
            "This is an educational/decision-support credit-readiness indicator "
            "based on the data you provided. It is not a bureau credit score, "
            "CIBIL score, or loan approval decision."
        ),
    )

    user = relationship("User", back_populates="credit_scores")
    factors = relationship("ScoreFactor", back_populates="credit_score", cascade="all, delete-orphan")

    # get_current_score() filters user_id + is_current on every credit-readiness
    # and recommendations call.
    __table_args__ = (Index("ix_credit_scores_user_current", "user_id", "is_current"),)


class ScoreFactor(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "score_factors"

    credit_score_id: Mapped[str] = mapped_column(String(36), ForeignKey("credit_scores.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    impact: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)  # signed point contribution
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # positive | negative | neutral
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    credit_score = relationship("CreditScore", back_populates="factors")
