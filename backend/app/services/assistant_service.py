"""
AI Financial Assistant (PRD Sections 19-20).

Architecture (per PRD Section 19):
    User Question -> AI Assistant -> Backend Financial Data ->
    Financial Analytics -> Structured Result -> AI Explanation

This module is rule-based by default so the assistant works correctly
with zero external dependencies (PRD Section 34 - modular ML/AI). It only
ever answers using structured data computed by analytics_service /
credit_readiness_service / recommendation_service - it never invents
transactions, scores, or guarantees (PRD Section 20).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import analytics_service, credit_readiness_service, recommendation_service

INSUFFICIENT_DATA_MESSAGE = (
    "I don't have enough consented financial data to answer that yet. "
    "Add some income and expense information, or click 'Load Demo Data' from the home screen, and I can help."
)


def _fmt_money(value: float) -> str:
    return f"\u20b9{value:,.0f}"


def _answer_spending(db: Session, user_id: str) -> tuple[str, bool]:
    breakdown = analytics_service.build_expense_breakdown(db, user_id)
    if not breakdown or not breakdown.get("categories"):
        return INSUFFICIENT_DATA_MESSAGE, True

    top = breakdown["categories"][0]
    return (
        f"Your largest spending category is **{top['category']}**, at {_fmt_money(top['amount'])} "
        f"({top['percentage_of_total']:.0f}% of your total expenses).",
        False,
    )


def _answer_can_save(db: Session, user_id: str, amount: float | None) -> tuple[str, bool]:
    savings = analytics_service.build_savings_analysis(db, user_id)
    if savings["average_monthly_surplus"] == 0 and savings["savings_rate"] is None:
        return INSUFFICIENT_DATA_MESSAGE, True

    surplus = savings["average_monthly_surplus"]
    if amount is None:
        amount = round(surplus * 0.7, 2) if surplus > 0 else 0

    if surplus <= 0:
        return (
            f"Based on your current data, your average monthly surplus is {_fmt_money(surplus)}, "
            "so committing to a fixed monthly saving amount right now could create financial stress. "
            "Consider reviewing non-essential expenses first.",
            False,
        )

    if amount <= surplus:
        return (
            f"Based on your average monthly surplus of {_fmt_money(surplus)}, saving {_fmt_money(amount)} "
            "per month looks fully achievable while keeping a safety buffer for unexpected costs.",
            False,
        )

    return (
        f"Saving {_fmt_money(amount)} per month may be tight - your average monthly surplus is currently "
        f"{_fmt_money(surplus)}. A target closer to {_fmt_money(round(surplus * 0.7, 2))} per month would be more realistic.",
        False,
    )


def _answer_why_score_changed(db: Session, user_id: str) -> tuple[str, bool]:
    from app.models.credit import CreditScore

    scores = (
        db.query(CreditScore)
        .filter(CreditScore.user_id == user_id)
        .order_by(CreditScore.created_at.desc())
        .limit(2)
        .all()
    )
    if len(scores) < 2:
        current = credit_readiness_service.get_current_score(db, user_id)
        if current:
            factors_text = ", ".join([f"{f.name} ({f.impact:+g} pts)" for f in current.factors])
            return (
                f"Your Credit Readiness Score is currently **{current.score}/100** ({current.rating}). "
                f"Main score drivers include: {factors_text}.",
                False,
            )
        return (
            "I only have one recorded credit-readiness score for you so far. "
            "As you record more financial activity and update consents, score changes will be tracked.",
            True,
        )

    latest, previous = scores[0], scores[1]
    diff = latest.score - previous.score
    direction = "increased" if diff > 0 else "decreased" if diff < 0 else "stayed the same"
    top_factors = sorted(latest.factors, key=lambda f: abs(f.impact), reverse=True)[:2]
    factor_text = "; ".join(f"{f.name}: {f.explanation}" for f in top_factors) if top_factors else ""

    message = (
        f"Your Credit Readiness Score {direction} from {previous.score} to {latest.score}"
        f"{f' ({diff:+d} points)' if diff != 0 else ''}."
    )
    if factor_text:
        message += f" Key factors: {factor_text}"

    return (message, False)


def _answer_what_changed(db: Session, user_id: str) -> tuple[str, bool]:
    summary = analytics_service.build_financial_summary(db, user_id)
    return (
        f"Here is your current financial summary: Total Income {_fmt_money(summary['total_income'])}, Total Expenses "
        f"{_fmt_money(summary['total_expenses'])}, Net Cash Flow {_fmt_money(summary['net_cash_flow'])}"
        + (f", and Savings Rate {summary['savings_rate']:.1f}%" if summary["savings_rate"] is not None else "")
        + ".",
        False,
    )


def _answer_before_loan(db: Session, user_id: str) -> tuple[str, bool]:
    recs = recommendation_service.generate_recommendations(db, user_id)
    borrowing_recs = [r for r in recs if r["category"] == "borrowing"]
    if borrowing_recs:
        return borrowing_recs[0]["message"], False
    summary = analytics_service.build_financial_summary(db, user_id)
    buffer_text = (
        f"{summary['emergency_buffer_months']} months"
        if summary["emergency_buffer_months"] is not None
        else "not yet calculated"
    )
    return (
        f"Before taking a loan, maintain an emergency buffer (currently {buffer_text}) and ensure new monthly repayments "
        "do not exceed 15-20% of your net monthly income.",
        False,
    )


def _answer_explain_health_simply(db: Session, user_id: str) -> tuple[str, bool]:
    if not analytics_service.has_minimum_data(db, user_id):
        return INSUFFICIENT_DATA_MESSAGE, True

    summary = analytics_service.build_financial_summary(db, user_id)
    classification_labels = {
        "HEALTHY": "Healthy",
        "STABLE": "Stable",
        "NEEDS_ATTENTION": "Needs Attention",
        "HIGH_RISK": "High Risk",
    }
    label = classification_labels.get(summary["classification"], summary["classification"])
    return (
        f"Your overall financial health is currently classified as **'{label}'**. Your monthly income is "
        f"{_fmt_money(summary['total_income'])} against expenses of {_fmt_money(summary['total_expenses'])}, leaving a "
        f"net cash flow of {_fmt_money(summary['net_cash_flow'])}.",
        False,
    )


def answer_question(db: Session, user_id: str, message: str) -> tuple[str, bool]:
    """
    Intelligent keyword and contextual routing for AI Assistant.
    """
    text = message.lower().strip()

    # 1. Score questions (e.g. "Why is my score 72?", "How is credit score calculated?", "Why score changed?")
    if any(k in text for k in ["score", "credit readiness", "credit score", "rating", "readiness"]):
        current_score = credit_readiness_service.get_current_score(db, user_id)
        if current_score:
            top_factors = sorted(current_score.factors, key=lambda f: abs(f.impact), reverse=True)
            positives = [f for f in top_factors if f.impact >= 0]
            negatives = [f for f in top_factors if f.impact < 0]
            
            parts = [f"Your Credit Readiness Score is currently **{current_score.score}/100** ({current_score.rating})."]
            if positives:
                pos_str = ", ".join([f"{f.name} (+{f.impact} pts)" for f in positives[:3]])
                parts.append(f"Strongest factors: {pos_str}.")
            if negatives:
                neg_str = ", ".join([f"{f.name} ({f.impact} pts)" for f in negatives[:2]])
                parts.append(f"Potential improvement areas: {neg_str}.")
            return (" ".join(parts), False)

        try:
            res = credit_readiness_service.calculate_credit_readiness(db, user_id)
            return (
                f"Your Credit Readiness Score is **{res['score']}/100** ({res['rating']}). "
                "This score is calculated transparently based on income stability, cash flow health, and emergency reserves.",
                False,
            )
        except credit_readiness_service.InsufficientDataError:
            return INSUFFICIENT_DATA_MESSAGE, True

    # 2. Spending questions (e.g. "Where am I spending the most?", "Top expenses?")
    if any(p in text for p in ["spend", "spending", "expense", "category", "where am i"]):
        return _answer_spending(db, user_id)

    # 3. Savings questions (e.g. "How can I save more?", "Can I save?")
    if any(p in text for p in ["save", "saving", "savings", "surplus", "buffer"]):
        import re
        amount = None
        match = re.search(r"[\u20b9]?\s?([\d,]+)", text)
        if match:
            try:
                amount = float(match.group(1).replace(",", ""))
            except ValueError:
                amount = None
        return _answer_can_save(db, user_id, amount)

    # 4. Loans & Borrowing
    if any(p in text for p in ["loan", "borrow", "debt", "repayment", "credit card"]):
        return _answer_before_loan(db, user_id)

    # 5. General Financial Overview / Greetings
    if any(p in text for p in ["hi", "hello", "help", "summary", "overview", "health", "explain", "detail"]):
        return _answer_explain_health_simply(db, user_id)

    # Default dynamic fallback
    if analytics_service.has_minimum_data(db, user_id):
        return _answer_explain_health_simply(db, user_id)

    return INSUFFICIENT_DATA_MESSAGE, True
