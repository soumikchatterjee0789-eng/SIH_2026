"""
Credit Readiness Engine (PRD Sections 14-17).

Rules enforced here:
  - Deterministic, weighted, fully explainable scoring (no black-box ML).
  - NEVER uses protected/sensitive attributes (PRD Section 15) - the data
    model doesn't even store them, and PROHIBITED_SCORING_ATTRIBUTES is
    checked defensively against the factor set as a guard-rail.
  - Returns INSUFFICIENT_DATA rather than a fabricated score when there
    isn't enough consented data yet (PRD Section 28).
  - Every score is stored with per-factor explanations and is fully
    recalculable from the user's current consented data.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.credit import CreditScore, ScoreFactor
from app.models.financial import IncomeRecord, BorrowingRecord
from app.config.thresholds import (
    CREDIT_READINESS_WEIGHTS,
    CREDIT_READINESS_RATING_BANDS,
    MIN_INCOME_RECORDS_FOR_CREDIT_READINESS,
    PROHIBITED_SCORING_ATTRIBUTES,
)
from app.services import analytics_service


class InsufficientDataError(Exception):
    pass


def _rating_for_score(score: int) -> str:
    for low, high, label in CREDIT_READINESS_RATING_BANDS:
        if low <= score <= high:
            return label
    return "Needs Improvement"


def _score_income_stability(db: Session, user_id: str) -> tuple[float, str, str]:
    """
    Simple, explainable stability heuristic: coefficient of variation of
    monthly income totals from income records + income transactions.
    Lower variation => higher stability => more points.
    """
    import statistics
    from collections import defaultdict

    monthly: dict[str, float] = defaultdict(float)
    for r in db.query(IncomeRecord).filter(IncomeRecord.user_id == user_id):
        monthly[r.record_date.strftime("%Y-%m")] += float(r.amount)

    from app.models.transaction import Transaction
    for t in db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.type == "income"):
        monthly[t.transaction_date.strftime("%Y-%m")] += float(t.amount)

    values = list(monthly.values())
    weight = CREDIT_READINESS_WEIGHTS["income_stability"]

    if len(values) < 2:
        # Not enough months to assess variability - award half credit and
        # say so explicitly, rather than pretending certainty either way.
        impact = round(weight * 0.5, 2)
        return impact, "positive", (
            "Only one period of income data is available, so stability could not be "
            "fully assessed. Partial credit was applied."
        )

    mean = statistics.mean(values)
    stdev = statistics.pstdev(values)
    cv = (stdev / mean) if mean > 0 else 1.0

    if cv <= 0.15:
        impact = weight
        explanation = "Income was relatively stable across the periods analyzed."
    elif cv <= 0.35:
        impact = round(weight * 0.6, 2)
        explanation = "Income showed moderate variation across the periods analyzed."
    else:
        impact = round(weight * 0.2, 2)
        explanation = "Income varied significantly across the periods analyzed."

    direction = "positive" if impact >= weight * 0.5 else "negative"
    return impact, direction, explanation


def _score_cash_flow_health(net_cash_flow: float, total_income: float) -> tuple[float, str, str]:
    weight = CREDIT_READINESS_WEIGHTS["cash_flow_health"]
    if total_income == 0:
        return 0.0, "negative", "No income has been recorded yet, so cash-flow health could not be assessed."

    ratio = net_cash_flow / total_income
    if ratio >= 0.2:
        impact = weight
        explanation = "Net cash flow is strongly positive relative to income."
    elif ratio >= 0.05:
        impact = round(weight * 0.65, 2)
        explanation = "Net cash flow is positive relative to income."
    elif ratio >= 0:
        impact = round(weight * 0.35, 2)
        explanation = "Net cash flow is close to break-even."
    else:
        impact = 0.0
        explanation = "Expenses currently exceed income, resulting in negative cash flow."

    direction = "positive" if impact >= weight * 0.5 else "negative"
    return impact, direction, explanation


def _score_savings_capacity(savings_rate: float | None) -> tuple[float, str, str]:
    weight = CREDIT_READINESS_WEIGHTS["savings_capacity"]
    if savings_rate is None:
        return 0.0, "negative", "Savings capacity could not be assessed without income data."

    if savings_rate >= 20:
        impact = weight
        explanation = "Savings capacity is strong relative to income."
    elif savings_rate >= 10:
        impact = round(weight * 0.7, 2)
        explanation = "The user consistently retained part of their monthly income."
    elif savings_rate >= 0:
        impact = round(weight * 0.35, 2)
        explanation = "Savings capacity is limited but positive."
    else:
        impact = 0.0
        explanation = "Spending currently exceeds income, leaving no savings capacity."

    direction = "positive" if impact >= weight * 0.5 else "negative"
    return impact, direction, explanation


def _score_expense_stability(db: Session, user_id: str) -> tuple[float, str, str]:
    import statistics
    from collections import defaultdict
    from app.models.financial import ExpenseRecord
    from app.models.transaction import Transaction

    monthly: dict[str, float] = defaultdict(float)
    for r in db.query(ExpenseRecord).filter(ExpenseRecord.user_id == user_id):
        monthly[r.record_date.strftime("%Y-%m")] += float(r.amount)
    for t in db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.type == "expense"):
        monthly[t.transaction_date.strftime("%Y-%m")] += float(t.amount)

    weight = CREDIT_READINESS_WEIGHTS["expense_stability"]
    values = list(monthly.values())

    if len(values) < 2:
        impact = round(weight * 0.5, 2)
        return impact, "positive", (
            "Only one period of expense data is available, so volatility could not be "
            "fully assessed. Partial credit was applied."
        )

    mean = statistics.mean(values)
    stdev = statistics.pstdev(values)
    cv = (stdev / mean) if mean > 0 else 1.0

    if cv <= 0.15:
        impact = weight
        explanation = "Monthly expenses were consistent across the periods analyzed."
    elif cv <= 0.35:
        impact = round(weight * 0.6, 2)
        explanation = "Monthly expenses showed some variation."
    else:
        impact = round(weight * 0.2, 2)
        explanation = "Monthly expenses showed significant variation."

    direction = "positive" if impact >= weight * 0.5 else "negative"
    return impact, direction, explanation


def _score_repayment_burden(db: Session, user_id: str, total_income: float) -> tuple[float, str, str]:
    weight = CREDIT_READINESS_WEIGHTS["repayment_burden"]
    borrowing = (
        db.query(BorrowingRecord)
        .filter(BorrowingRecord.user_id == user_id)
        .order_by(BorrowingRecord.record_date.desc())
        .first()
    )

    if borrowing is None or float(borrowing.monthly_repayment) == 0:
        return weight, "positive", "No existing repayment obligations were reported."

    if total_income == 0:
        return 0.0, "negative", "Existing repayment obligations could not be assessed without income data."

    # Approximate monthly income for a burden ratio.
    months = analytics_service._count_distinct_months(db, user_id)
    avg_monthly_income = total_income / months if months else total_income
    burden_ratio = float(borrowing.monthly_repayment) / avg_monthly_income if avg_monthly_income else 1.0

    if burden_ratio <= 0.15:
        impact = weight
        explanation = "Existing repayment obligations are low relative to income."
    elif burden_ratio <= 0.35:
        impact = round(weight * 0.5, 2)
        explanation = "Existing repayment obligations are moderate relative to income."
    else:
        impact = 0.0
        explanation = "Existing repayment obligations are high relative to income."

    direction = "positive" if impact >= weight * 0.5 else "negative"
    return impact, direction, explanation


def _score_emergency_buffer(months: float | None) -> tuple[float, str, str]:
    weight = CREDIT_READINESS_WEIGHTS["emergency_buffer"]
    if months is None:
        return 0.0, "negative", "Emergency buffer could not be assessed - no savings snapshot was found."

    if months >= 6:
        impact = weight
        explanation = "Emergency buffer comfortably covers essential expenses for 6+ months."
    elif months >= 3:
        impact = round(weight * 0.7, 2)
        explanation = "Emergency buffer covers essential expenses for 3-6 months."
    elif months >= 1:
        impact = round(weight * 0.35, 2)
        explanation = "Emergency buffer is low, covering essential expenses for 1-3 months."
    else:
        impact = 0.0
        explanation = "Emergency buffer is very low or unavailable."

    direction = "positive" if impact >= weight * 0.5 else "negative"
    return impact, direction, explanation


def has_sufficient_data_for_score(db: Session, user_id: str) -> bool:
    income_count = db.query(IncomeRecord).filter(IncomeRecord.user_id == user_id).count()
    from app.models.transaction import Transaction
    income_txn_count = (
        db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.type == "income").count()
    )
    return (income_count + income_txn_count) >= MIN_INCOME_RECORDS_FOR_CREDIT_READINESS


def calculate_credit_readiness(db: Session, user_id: str) -> dict:
    """
    Computes the full score + factor breakdown. Raises InsufficientDataError
    if there isn't enough consented data yet - callers must translate this
    into the INSUFFICIENT_DATA API error, never a fabricated 0.
    """
    if not has_sufficient_data_for_score(db, user_id):
        raise InsufficientDataError(
            "Credit readiness cannot be calculated yet because more consented financial information is required."
        )

    summary = analytics_service.build_financial_summary(db, user_id)

    factors = []

    impact, direction, explanation = _score_income_stability(db, user_id)
    factors.append({"name": "Income Stability", "impact": impact, "direction": direction, "explanation": explanation})

    impact, direction, explanation = _score_cash_flow_health(summary["net_cash_flow"], summary["total_income"])
    factors.append({"name": "Cash Flow Health", "impact": impact, "direction": direction, "explanation": explanation})

    impact, direction, explanation = _score_savings_capacity(summary["savings_rate"])
    factors.append({"name": "Savings Capacity", "impact": impact, "direction": direction, "explanation": explanation})

    impact, direction, explanation = _score_expense_stability(db, user_id)
    factors.append({"name": "Expense Stability", "impact": impact, "direction": direction, "explanation": explanation})

    impact, direction, explanation = _score_repayment_burden(db, user_id, summary["total_income"])
    factors.append(
        {"name": "Existing Repayment Burden", "impact": impact, "direction": direction, "explanation": explanation}
    )

    impact, direction, explanation = _score_emergency_buffer(summary["emergency_buffer_months"])
    factors.append({"name": "Emergency Buffer", "impact": impact, "direction": direction, "explanation": explanation})

    # Defensive guard-rail: assert no factor name maps to a prohibited attribute.
    for f in factors:
        assert f["name"].lower().replace(" ", "_") not in PROHIBITED_SCORING_ATTRIBUTES

    raw_score = sum(f["impact"] for f in factors)
    score = max(0, min(100, round(raw_score)))
    rating = _rating_for_score(score)

    return {"score": score, "rating": rating, "factors": factors}


def save_credit_score(db: Session, user_id: str, result: dict) -> CreditScore:
    # Mark previous scores as not current (history is preserved, not deleted).
    db.query(CreditScore).filter(CreditScore.user_id == user_id, CreditScore.is_current.is_(True)).update(
        {"is_current": False}
    )

    credit_score = CreditScore(user_id=user_id, score=result["score"], rating=result["rating"], is_current=True)
    db.add(credit_score)
    db.flush()  # get credit_score.id before adding factors

    for f in result["factors"]:
        db.add(
            ScoreFactor(
                credit_score_id=credit_score.id,
                name=f["name"],
                impact=f["impact"],
                direction=f["direction"],
                explanation=f["explanation"],
            )
        )

    db.commit()
    db.refresh(credit_score)
    return credit_score


def get_current_score(db: Session, user_id: str) -> CreditScore | None:
    return (
        db.query(CreditScore)
        .filter(CreditScore.user_id == user_id, CreditScore.is_current.is_(True))
        .order_by(CreditScore.created_at.desc())
        .first()
    )
