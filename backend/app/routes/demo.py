"""
Demo mode (PRD Section 29 + Section 40 nice-to-have).

Seeds clearly-labelled synthetic financial data for the current user so
the dashboard, credit-readiness engine, and assistant can be demonstrated
end-to-end without requiring real financial information. Demo data is
tagged distinctly (source descriptions prefixed with "[DEMO]") so it can
never be confused with real user data.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.financial import IncomeRecord, ExpenseRecord, SavingsRecord, BorrowingRecord
from app.utils.response import success_response
from app.utils.deps import get_current_user
from app.services import consent_service
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/demo", tags=["Demo"])

DEMO_CATEGORIES = ["income", "expenses", "savings", "borrowing"]


@router.post("/seed")
def seed_demo_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Grants demo consents and inserts synthetic data matching PRD Section 29."""
    for category in DEMO_CATEGORIES:
        consent_service.grant_consent(db, user.id, category, purpose=None)

    today = date.today()

    db.add(IncomeRecord(
        user_id=user.id, source="[DEMO] Salary/Business Income", amount=25000,
        frequency="monthly", record_date=today.replace(day=1),
    ))
    db.add(IncomeRecord(
        user_id=user.id, source="[DEMO] Salary/Business Income", amount=24500,
        frequency="monthly", record_date=(today.replace(day=1) - timedelta(days=30)),
    ))

    expense_plan = [("Rent/Hostel", 8000), ("Food", 5500), ("Transport", 2000), ("Utilities", 1500), ("Education", 1500)]
    for category, amount in expense_plan:
        db.add(ExpenseRecord(
            user_id=user.id, category=category, amount=amount,
            frequency="monthly", record_date=today.replace(day=5),
        ))

    db.add(SavingsRecord(
        user_id=user.id, current_savings=32000, monthly_savings=6500,
        emergency_savings=20000, record_date=today,
    ))

    db.add(BorrowingRecord(
        user_id=user.id, existing_loan_amount=15000, monthly_repayment=2500,
        remaining_period_months=6, record_date=today,
    ))

    db.commit()
    log_action(db, user.id, "DATA_CREATED", "demo_seed", new_value="Synthetic demo dataset seeded")

    return success_response(
        None,
        message="Demo data seeded. This is clearly-labelled synthetic data for demonstration purposes only.",
    )
