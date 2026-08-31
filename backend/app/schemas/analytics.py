from pydantic import BaseModel


class FinancialSummaryOut(BaseModel):
    total_income: float
    total_expenses: float
    net_cash_flow: float
    savings_rate: float | None
    expense_ratio: float | None
    emergency_buffer_months: float | None
    emergency_buffer_status: str | None
    classification: str
    insight_notes: list[str] = []


class CashFlowPointOut(BaseModel):
    period: str  # e.g. "2026-08"
    income: float
    expenses: float
    net: float


class CashFlowOut(BaseModel):
    points: list[CashFlowPointOut]


class ExpenseCategoryOut(BaseModel):
    category: str
    amount: float
    percentage_of_total: float


class ExpenseBreakdownOut(BaseModel):
    total_expenses: float
    categories: list[ExpenseCategoryOut]


class SavingsAnalysisOut(BaseModel):
    savings_rate: float | None
    average_monthly_surplus: float
    current_savings: float
    emergency_savings: float
    emergency_buffer_months: float | None
    projected_12_month_savings_at_current_rate: float | None
