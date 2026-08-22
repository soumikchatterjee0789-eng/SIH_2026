"""
Financial Health Engine (PRD Sections 11-13).

This module is the single source of truth for every financial number
shown anywhere in the product. The frontend must never recompute these
figures independently (PRD Section 32) - it only renders what this
service returns via the API.

All calculations combine consented manual records (income_records,
expense_records) AND consented uploaded transactions, since both are
valid inputs to "how much money came in / went out".
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.financial import IncomeRecord, ExpenseRecord, SavingsRecord
from app.models.transaction import Transaction
from app.config.thresholds import (
    FINANCIAL_HEALTH_THRESHOLDS,
    FINANCIAL_HEALTH_ORDER,
    EMERGENCY_BUFFER_THRESHOLDS,
)


def _to_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value) if value is not None else 0.0


def get_total_income(db: Session, user_id: str) -> float:
    manual = sum(_to_float(r.amount) for r in db.query(IncomeRecord).filter(IncomeRecord.user_id == user_id))
    from_txns = sum(
        _to_float(t.amount)
        for t in db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.type == "income")
    )
    return round(manual + from_txns, 2)


def get_total_expenses(db: Session, user_id: str) -> float:
    manual = sum(_to_float(r.amount) for r in db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id))
    from_txns = sum(
        _to_float(t.amount)
        for t in db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.type == "expense")
    )
    return round(manual + from_txns, 2)


def get_net_cash_flow(total_income: float, total_expenses: float) -> float:
    """Net Cash Flow = Total Income - Total Expenses (PRD Section 12)"""
    return round(total_income - total_expenses, 2)


def get_savings_rate(net_cash_flow: float, total_income: float) -> float | None:
    """
    Savings Rate = (Net Cash Flow / Total Income) x 100
    Never divide by zero - if income is zero, return None (PRD Section 12).
    """
    if total_income == 0:
        return None
    return round((net_cash_flow / total_income) * 100, 2)


def get_expense_ratio(total_expenses: float, total_income: float) -> float | None:
    """Expense Ratio = (Total Expenses / Total Income) x 100"""
    if total_income == 0:
        return None
    return round((total_expenses / total_income) * 100, 2)


def get_latest_savings_snapshot(db: Session, user_id: str) -> SavingsRecord | None:
    return (
        db.query(SavingsRecord)
        .filter(SavingsRecord.user_id == user_id)
        .order_by(SavingsRecord.record_date.desc(), SavingsRecord.created_at.desc())
        .first()
    )


def get_average_monthly_essential_expenses(db: Session, user_id: str) -> float:
    """
    Approximates average monthly essential expenses from expense records +
    transactions tagged with essential categories. Falls back to overall
    average monthly expenses if no category data exists.
    """
    essential_categories = {"Food", "Rent/Hostel", "Education", "Transport", "Utilities", "Healthcare"}

    monthly_totals: dict[str, float] = defaultdict(float)

    for r in db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id):
        if r.category in essential_categories:
            key = r.record_date.strftime("%Y-%m")
            monthly_totals[key] += _to_float(r.amount)

    for t in db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.type == "expense"):
        if t.category in essential_categories:
            key = t.transaction_date.strftime("%Y-%m")
            monthly_totals[key] += _to_float(t.amount)

    if not monthly_totals:
        # Fall back to all expenses if nothing was tagged essential.
        total_expenses = get_total_expenses(db, user_id)
        months = _count_distinct_months(db, user_id)
        return round(total_expenses / months, 2) if months else 0.0

    return round(sum(monthly_totals.values()) / len(monthly_totals), 2)


def _count_distinct_months(db: Session, user_id: str) -> int:
    months = set()
    for r in db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id):
        months.add(r.record_date.strftime("%Y-%m"))
    for t in db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.type == "expense"):
        months.add(t.transaction_date.strftime("%Y-%m"))
    return len(months) or 1


def get_emergency_buffer_months(db: Session, user_id: str) -> float | None:
    """
    Emergency Buffer = Available Emergency Savings / Average Monthly
    Essential Expenses, returned in months (PRD Section 12).
    """
    snapshot = get_latest_savings_snapshot(db, user_id)
    if snapshot is None:
        return None

    avg_essential = get_average_monthly_essential_expenses(db, user_id)
    if avg_essential == 0:
        return None

    return round(_to_float(snapshot.emergency_savings) / avg_essential, 2)


def classify_emergency_buffer(months: float | None) -> str | None:
    if months is None:
        return None
    if months >= EMERGENCY_BUFFER_THRESHOLDS["STRONG"]:
        return "Strong"
    if months >= EMERGENCY_BUFFER_THRESHOLDS["ADEQUATE"]:
        return "Adequate"
    if months >= EMERGENCY_BUFFER_THRESHOLDS["LOW"]:
        return "Low"
    return "Critical"


def classify_financial_health(savings_rate: float | None, expense_ratio: float | None) -> str:
    """
    Applies FINANCIAL_HEALTH_THRESHOLDS top-down (PRD Section 13).
    If savings_rate is None (zero income), we cannot respectably classify
    better than HIGH_RISK / needs-data, so we return NEEDS_ATTENTION with
    the honest caveat handled by the caller via insight_notes.
    """
    if savings_rate is None or expense_ratio is None:
        return "NEEDS_ATTENTION"

    for bucket_name in FINANCIAL_HEALTH_ORDER:
        bucket = FINANCIAL_HEALTH_THRESHOLDS[bucket_name]
        if savings_rate >= bucket["min_savings_rate"] and expense_ratio <= bucket["max_expense_ratio"]:
            return bucket_name
    return "HIGH_RISK"


def has_minimum_data(db: Session, user_id: str) -> bool:
    has_income = db.query(IncomeRecord).filter(IncomeRecord.user_id == user_id).first() is not None
    has_expense = db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id).first() is not None
    has_txn = db.query(Transaction).filter(Transaction.user_id == user_id).first() is not None
    return has_income or has_expense or has_txn


def build_financial_summary(db: Session, user_id: str) -> dict:
    total_income = get_total_income(db, user_id)
    total_expenses = get_total_expenses(db, user_id)
    net_cash_flow = get_net_cash_flow(total_income, total_expenses)
    savings_rate = get_savings_rate(net_cash_flow, total_income)
    expense_ratio = get_expense_ratio(total_expenses, total_income)
    emergency_buffer_months = get_emergency_buffer_months(db, user_id)
    emergency_buffer_status = classify_emergency_buffer(emergency_buffer_months)
    classification = classify_financial_health(savings_rate, expense_ratio)

    notes = []
    if total_income == 0:
        notes.append("No income has been recorded yet, so savings rate and expense ratio cannot be calculated.")
    if emergency_buffer_months is None:
        notes.append("Add a savings snapshot to see your emergency buffer in months.")

    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_cash_flow": net_cash_flow,
        "savings_rate": savings_rate,
        "expense_ratio": expense_ratio,
        "emergency_buffer_months": emergency_buffer_months,
        "emergency_buffer_status": emergency_buffer_status,
        "classification": classification,
        "insight_notes": notes,
    }


def build_cash_flow_series(db: Session, user_id: str) -> list[dict]:
    """Groups income/expenses by calendar month (YYYY-MM) across manual
    records and transactions."""
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})

    for r in db.query(IncomeRecord).filter(IncomeRecord.user_id == user_id):
        key = r.record_date.strftime("%Y-%m")
        monthly[key]["income"] += _to_float(r.amount)

    for r in db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id):
        key = r.record_date.strftime("%Y-%m")
        monthly[key]["expenses"] += _to_float(r.amount)

    for t in db.query(Transaction).filter(Transaction.user_id == user_id):
        key = t.transaction_date.strftime("%Y-%m")
        if t.type == "income":
            monthly[key]["income"] += _to_float(t.amount)
        else:
            monthly[key]["expenses"] += _to_float(t.amount)

    points = []
    for period in sorted(monthly.keys()):
        income = round(monthly[period]["income"], 2)
        expenses = round(monthly[period]["expenses"], 2)
        points.append({"period": period, "income": income, "expenses": expenses, "net": round(income - expenses, 2)})
    return points


def build_expense_breakdown(db: Session, user_id: str) -> dict:
    totals: dict[str, float] = defaultdict(float)

    for r in db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id):
        totals[r.category] += _to_float(r.amount)

    for t in db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.type == "expense"):
        totals[t.category] += _to_float(t.amount)

    total_expenses = round(sum(totals.values()), 2)
    categories = []
    for category, amount in sorted(totals.items(), key=lambda kv: kv[1], reverse=True):
        pct = round((amount / total_expenses) * 100, 2) if total_expenses > 0 else 0.0
        categories.append({"category": category, "amount": round(amount, 2), "percentage_of_total": pct})

    return {"total_expenses": total_expenses, "categories": categories}


def build_savings_analysis(db: Session, user_id: str) -> dict:
    total_income = get_total_income(db, user_id)
    total_expenses = get_total_expenses(db, user_id)
    net_cash_flow = get_net_cash_flow(total_income, total_expenses)
    savings_rate = get_savings_rate(net_cash_flow, total_income)

    months = _count_distinct_months(db, user_id)
    average_monthly_surplus = round(net_cash_flow / months, 2) if months else net_cash_flow

    snapshot = get_latest_savings_snapshot(db, user_id)
    current_savings = _to_float(snapshot.current_savings) if snapshot else 0.0
    emergency_savings = _to_float(snapshot.emergency_savings) if snapshot else 0.0
    emergency_buffer_months = get_emergency_buffer_months(db, user_id)

    projected = None
    if average_monthly_surplus is not None:
        projected = round(current_savings + (average_monthly_surplus * 12), 2)

    return {
        "savings_rate": savings_rate,
        "average_monthly_surplus": average_monthly_surplus,
        "current_savings": current_savings,
        "emergency_savings": emergency_savings,
        "emergency_buffer_months": emergency_buffer_months,
        "projected_12_month_savings_at_current_rate": projected,
    }
