from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.analytics import FinancialSummaryOut, CashFlowOut, ExpenseBreakdownOut, SavingsAnalysisOut
from app.utils.response import success_response
from app.utils.deps import get_current_user
from app.services import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

# Note: analytics endpoints intentionally do not gate on a single consent
# category dependency, since they blend income + expenses + savings. Each
# underlying query only reads records that exist - and records only exist
# if their category's consent was active at creation time and hasn't since
# had all data deleted. For stricter enforcement, combine with consent
# checks client-side via GET /api/consents before surfacing this data.


@router.get("/summary")
def get_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    summary = analytics_service.build_financial_summary(db, user.id)
    return success_response(FinancialSummaryOut(**summary).model_dump(mode="json"))


@router.get("/cash-flow")
def get_cash_flow(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    points = analytics_service.build_cash_flow_series(db, user.id)
    return success_response(CashFlowOut(points=points).model_dump(mode="json"))


@router.get("/expenses")
def get_expenses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    breakdown = analytics_service.build_expense_breakdown(db, user.id)
    return success_response(ExpenseBreakdownOut(**breakdown).model_dump(mode="json"))


@router.get("/savings")
def get_savings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = analytics_service.build_savings_analysis(db, user.id)
    return success_response(SavingsAnalysisOut(**analysis).model_dump(mode="json"))
