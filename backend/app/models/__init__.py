"""
Importing this package registers every ORM model against Base.metadata,
which is required for `Base.metadata.create_all()` to create all tables.
"""
from app.models.user import User, UserType  # noqa: F401
from app.models.consent import Consent  # noqa: F401
from app.models.financial import (  # noqa: F401
    FinancialProfile,
    IncomeRecord,
    ExpenseRecord,
    SavingsRecord,
    BorrowingRecord,
)
from app.models.transaction import Transaction  # noqa: F401
from app.models.metrics import FinancialMetric  # noqa: F401
from app.models.credit import CreditScore, ScoreFactor  # noqa: F401
from app.models.recommendation import Recommendation  # noqa: F401
from app.models.assistant import AssistantConversation  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
