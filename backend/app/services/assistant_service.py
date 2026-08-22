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

If settings.AI_API_KEY is configured, `phrase_with_llm()` can be used by
a future iteration to *rephrase* an already-computed structured answer in
more natural language. It must never be used to invent the underlying
numbers themselves - the compute-then-phrase separation is intentional
and MUST be preserved by anyone extending this module.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import analytics_service, credit_readiness_service, recommendation_service

INSUFFICIENT_DATA_MESSAGE = (
    "I don't have enough consented financial data to answer that yet. "
    "Add some income and expense information, or upload a transaction CSV, and I can help."
)


def _fmt_money(value: float) -> str:
    return f"\u20b9{value:,.0f}"


def _answer_spending(db: Session, user_id: str) -> tuple[str, bool]:
    breakdown = analytics_service.build_expense_breakdown(db, user_id)
    if not breakdown["categories"]:
        return INSUFFICIENT_DATA_MESSAGE, True

    top = breakdown["categories"][0]
    return (
        f"Your largest spending category is {top['category']}, at {_fmt_money(top['amount'])} "
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
            "Consider reviewing expenses first.",
            False,
        )

    if amount <= surplus:
        return (
            f"Based on your average monthly surplus of {_fmt_money(surplus)}, saving {_fmt_money(amount)} "
            "per month looks achievable, though it's a good idea to keep some buffer for unexpected costs.",
            False,
        )

    return (
        f"Saving {_fmt_money(amount)} per month may be difficult - your average monthly surplus is currently "
        f"only {_fmt_money(surplus)}. A target closer to {_fmt_money(round(surplus * 0.7, 2))} may be more realistic.",
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
        return (
            "I only have one recorded credit-readiness score for you so far, so there's no change to explain yet. "
            "Once your data updates and the score recalculates, I can compare the two.",
            True,
        )

    latest, previous = scores[0], scores[1]
    diff = latest.score - previous.score
    direction = "increased" if diff > 0 else "decreased" if diff < 0 else "stayed the same"
    top_factors = sorted(latest.factors, key=lambda f: abs(f.impact), reverse=True)[:2]
    factor_text = "; ".join(f"{f.name}: {f.explanation}" for f in top_factors) if top_factors else ""

    return (
        f"Your Credit Readiness Score {direction} from {previous.score} to {latest.score}"
        f"{f' ({diff:+d} points)' if diff != 0 else ''}. "
        f"Key factors: {factor_text}" if factor_text else "",
        False,
    )


def _answer_what_changed(db: Session, user_id: str) -> tuple[str, bool]:
    summary = analytics_service.build_financial_summary(db, user_id)
    return (
        f"Right now: total income {_fmt_money(summary['total_income'])}, total expenses "
        f"{_fmt_money(summary['total_expenses'])}, net cash flow {_fmt_money(summary['net_cash_flow'])}"
        + (f", savings rate {summary['savings_rate']:.1f}%" if summary["savings_rate"] is not None else "")
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
        f"Before considering a loan, review your emergency buffer (currently {buffer_text}) and make sure a new "
        "repayment wouldn't significantly reduce your savings capacity. This is guidance, not a loan approval.",
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
        f"Your financial health is currently classified as '{label}'. You're bringing in "
        f"{_fmt_money(summary['total_income'])} and spending {_fmt_money(summary['total_expenses'])}, leaving a "
        f"net cash flow of {_fmt_money(summary['net_cash_flow'])}.",
        False,
    )


def answer_question(db: Session, user_id: str, message: str) -> tuple[str, bool]:
    """
    Returns (answer_text, used_insufficient_data_fallback).
    Pure keyword routing - simple, transparent, and fully auditable, per
    PRD Section 35's preference for transparent logic over black boxes.
    """
    text = message.lower().strip()

    if any(p in text for p in ["spending the most", "spend the most", "biggest expense", "largest expense", "where am i spending"]):
        return _answer_spending(db, user_id)

    if "save" in text and ("can i" in text or "should i" in text or "afford" in text):
        import re

        amount = None
        match = re.search(r"[\u20b9]?\s?([\d,]+)", text)
        if match:
            try:
                amount = float(match.group(1).replace(",", ""))
            except ValueError:
                amount = None
        return _answer_can_save(db, user_id, amount)

    if "why" in text and "score" in text and ("decrease" in text or "drop" in text or "change" in text or "increase" in text):
        return _answer_why_score_changed(db, user_id)

    if "what changed" in text or ("changed" in text and "month" in text):
        return _answer_what_changed(db, user_id)

    if "before" in text and ("loan" in text or "borrow" in text or "credit" in text):
        return _answer_before_loan(db, user_id)

    if "explain" in text and ("health" in text or "simply" in text or "simple" in text):
        return _answer_explain_health_simply(db, user_id)

    if "credit readiness" in text or "credit score" in text:
        try:
            result = credit_readiness_service.calculate_credit_readiness(db, user_id)
            return (
                f"Your current Credit Readiness indicator is {result['score']}/100 ({result['rating']}). "
                "Remember, this is an educational indicator, not an official bureau credit score.",
                False,
            )
        except credit_readiness_service.InsufficientDataError:
            return INSUFFICIENT_DATA_MESSAGE, True

    # Default fallback: give a general financial-health snapshot if data
    # exists, otherwise say plainly that there isn't enough data - never
    # guess (PRD Section 20).
    if analytics_service.has_minimum_data(db, user_id):
        return _answer_explain_health_simply(db, user_id)

    return INSUFFICIENT_DATA_MESSAGE, True
