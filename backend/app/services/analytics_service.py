"""
Financial Health Engine (PRD Sections 11-13).

This module is the single source of truth for every financial number
shown anywhere in the product. The frontend must never recompute these
figures independently (PRD Section 32) - it only renders what this
service returns via the API.

All calculations combine consented manual records (income_records,
expense_records) AND consented uploaded transactions, since both are
valid inputs to "how much money came in / went out".

Monthly/category grouping (cash-flow series, expense breakdown, average
essential expenses) is done with pandas - the Financial Analytics Engine
named in the project's technical approach - rather than hand-rolled
dictionaries, so the same grouping logic is used everywhere and is easy
to extend (e.g. resampling to weekly/quarterly) without rewriting loops.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
from sqlalchemy.orm import Session

from app.models.financial import IncomeRecord, ExpenseRecord, SavingsRecord
from app.models.transaction import Transaction
from app.config.thresholds import (
    FINANCIAL_HEALTH_THRESHOLDS,
    FINANCIAL_HEALTH_ORDER,
    EMERGENCY_BUFFER_THRESHOLDS,
)
from app.services.consent_service import get_active_consent_categories


def _to_float(value) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value) if value is not None else 0.0


def get_total_income(db: Session, user_id: str, active: set[str] | None = None) -> float:
    active = get_active_consent_categories(db, user_id) if active is None else active
    manual = 0.0
    if "income" in active:
        manual = sum(_to_float(r.amount) for r in db.query(IncomeRecord).filter(IncomeRecord.user_id == user_id))
    from_txns = 0.0
    if "transactions" in active:
        from_txns = sum(
            _to_float(t.amount)
            for t in db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.type == "income")
        )
    return round(manual + from_txns, 2)


def get_total_expenses(db: Session, user_id: str, active: set[str] | None = None) -> float:
    active = get_active_consent_categories(db, user_id) if active is None else active
    manual = 0.0
    if "expenses" in active:
        manual = sum(_to_float(r.amount) for r in db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id))
    from_txns = 0.0
    if "transactions" in active:
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


def get_latest_savings_snapshot(db: Session, user_id: str, active: set[str] | None = None) -> SavingsRecord | None:
    active = get_active_consent_categories(db, user_id) if active is None else active
    if "savings" not in active:
        return None
    return (
        db.query(SavingsRecord)
        .filter(SavingsRecord.user_id == user_id)
        .order_by(SavingsRecord.record_date.desc(), SavingsRecord.created_at.desc())
        .first()
    )


def _expense_dataframe(db: Session, user_id: str, active: set[str]) -> pd.DataFrame:
    """Combines consented ExpenseRecord + expense-type Transaction rows into
    one DataFrame with columns [month, category, amount], the shape every
    expense-grouping function below needs."""
    rows: list[dict] = []
    if "expenses" in active:
        for r in db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id):
            rows.append({"month": r.record_date.strftime("%Y-%m"), "category": r.category, "amount": _to_float(r.amount)})
    if "transactions" in active:
        for t in db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.type == "expense"):
            rows.append({"month": t.transaction_date.strftime("%Y-%m"), "category": t.category, "amount": _to_float(t.amount)})
    return pd.DataFrame(rows, columns=["month", "category", "amount"])


def get_average_monthly_essential_expenses(db: Session, user_id: str, active: set[str] | None = None) -> float:
    """
    Approximates average monthly essential expenses from expense records +
    transactions tagged with essential categories. Falls back to overall
    average monthly expenses if no category data exists.
    """
    active = get_active_consent_categories(db, user_id) if active is None else active
    essential_categories = {"Food", "Rent/Hostel", "Education", "Transport", "Utilities", "Healthcare"}

    df = _expense_dataframe(db, user_id, active)
    essential = df[df["category"].isin(essential_categories)] if not df.empty else df

    if essential.empty:
        # Fall back to all expenses if nothing was tagged essential.
        total_expenses = get_total_expenses(db, user_id, active)
        months = _count_distinct_months(db, user_id, active)
        return round(total_expenses / months, 2) if months else 0.0

    monthly_totals = essential.groupby("month")["amount"].sum()
    return round(float(monthly_totals.mean()), 2)


def _count_distinct_months(db: Session, user_id: str, active: set[str] | None = None) -> int:
    active = get_active_consent_categories(db, user_id) if active is None else active
    df = _expense_dataframe(db, user_id, active)
    return int(df["month"].nunique()) or 1


def get_emergency_buffer_months(db: Session, user_id: str, active: set[str] | None = None) -> float | None:
    """
    Emergency Buffer = Available Emergency Savings / Average Monthly
    Essential Expenses, returned in months (PRD Section 12).
    """
    active = get_active_consent_categories(db, user_id) if active is None else active
    snapshot = get_latest_savings_snapshot(db, user_id, active)
    if snapshot is None:
        return None

    avg_essential = get_average_monthly_essential_expenses(db, user_id, active)
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


def has_minimum_data(db: Session, user_id: str, active: set[str] | None = None) -> bool:
    active = get_active_consent_categories(db, user_id) if active is None else active
    has_income = (
        "income" in active
        and db.query(IncomeRecord).filter(IncomeRecord.user_id == user_id).first() is not None
    )
    has_expense = (
        "expenses" in active
        and db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id).first() is not None
    )
    has_txn = (
        "transactions" in active
        and db.query(Transaction).filter(Transaction.user_id == user_id).first() is not None
    )
    return has_income or has_expense or has_txn


def build_financial_summary(db: Session, user_id: str) -> dict:
    active = get_active_consent_categories(db, user_id)
    total_income = get_total_income(db, user_id, active)
    total_expenses = get_total_expenses(db, user_id, active)
    net_cash_flow = get_net_cash_flow(total_income, total_expenses)
    savings_rate = get_savings_rate(net_cash_flow, total_income)
    expense_ratio = get_expense_ratio(total_expenses, total_income)
    emergency_buffer_months = get_emergency_buffer_months(db, user_id, active)
    emergency_buffer_status = classify_emergency_buffer(emergency_buffer_months)
    classification = classify_financial_health(savings_rate, expense_ratio)

    notes = []
    if total_income == 0:
        if "income" not in active and "transactions" not in active:
            notes.append("Grant consent for income or transaction data to see your savings rate and expense ratio.")
        else:
            notes.append("No income has been recorded yet, so savings rate and expense ratio cannot be calculated.")
    if emergency_buffer_months is None:
        if "savings" not in active:
            notes.append("Grant consent for savings data to see your emergency buffer in months.")
        else:
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
    records and transactions, using a pandas pivot so income and expense
    columns line up per month in one pass."""
    active = get_active_consent_categories(db, user_id)
    rows: list[dict] = []

    if "income" in active:
        for r in db.query(IncomeRecord).filter(IncomeRecord.user_id == user_id):
            rows.append({"month": r.record_date.strftime("%Y-%m"), "flow": "income", "amount": _to_float(r.amount)})

    if "expenses" in active:
        for r in db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id):
            rows.append({"month": r.record_date.strftime("%Y-%m"), "flow": "expenses", "amount": _to_float(r.amount)})

    if "transactions" in active:
        for t in db.query(Transaction).filter(Transaction.user_id == user_id):
            flow = "income" if t.type == "income" else "expenses"
            rows.append({"month": t.transaction_date.strftime("%Y-%m"), "flow": flow, "amount": _to_float(t.amount)})

    if not rows:
        return []

    df = pd.DataFrame(rows)
    pivot = df.pivot_table(index="month", columns="flow", values="amount", aggfunc="sum", fill_value=0.0)
    pivot = pivot.reindex(columns=["income", "expenses"], fill_value=0.0).sort_index()

    points = []
    for period, row in pivot.iterrows():
        income = round(float(row["income"]), 2)
        expenses = round(float(row["expenses"]), 2)
        points.append({"period": period, "income": income, "expenses": expenses, "net": round(income - expenses, 2)})
    return points


def build_expense_breakdown(db: Session, user_id: str) -> dict:
    active = get_active_consent_categories(db, user_id)
    df = _expense_dataframe(db, user_id, active)

    if df.empty:
        return {"total_expenses": 0.0, "categories": []}

    by_category = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    total_expenses = round(float(by_category.sum()), 2)

    categories = []
    for category, amount in by_category.items():
        amount = float(amount)
        pct = round((amount / total_expenses) * 100, 2) if total_expenses > 0 else 0.0
        categories.append({"category": category, "amount": round(amount, 2), "percentage_of_total": pct})

    return {"total_expenses": total_expenses, "categories": categories}


def build_savings_analysis(db: Session, user_id: str) -> dict:
    active = get_active_consent_categories(db, user_id)
    total_income = get_total_income(db, user_id, active)
    total_expenses = get_total_expenses(db, user_id, active)
    net_cash_flow = get_net_cash_flow(total_income, total_expenses)
    savings_rate = get_savings_rate(net_cash_flow, total_income)

    months = _count_distinct_months(db, user_id, active)
    average_monthly_surplus = round(net_cash_flow / months, 2) if months else net_cash_flow

    snapshot = get_latest_savings_snapshot(db, user_id, active)
    current_savings = _to_float(snapshot.current_savings) if snapshot else 0.0
    emergency_savings = _to_float(snapshot.emergency_savings) if snapshot else 0.0
    emergency_buffer_months = get_emergency_buffer_months(db, user_id, active)

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
