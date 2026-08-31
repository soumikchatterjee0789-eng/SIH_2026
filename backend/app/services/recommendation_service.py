"""
Recommendation Engine (PRD Section 18).

Recommendations are explainable, based on available data, non-judgmental,
actionable, and clearly labelled as guidance - never as approval or advice
that substitutes for a licensed financial advisor.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation
from app.models.financial import BorrowingRecord
from app.services import analytics_service
from app.services import spending_insights_service
from app.services.consent_service import get_active_consent_categories


def generate_recommendations(db: Session, user_id: str) -> list[dict]:
    summary = analytics_service.build_financial_summary(db, user_id)
    breakdown = analytics_service.build_expense_breakdown(db, user_id)
    recs: list[dict] = []

    # --- Savings recommendation ---
    surplus = summary["net_cash_flow"]
    if summary["total_income"] == 0:
        recs.append(
            {
                "category": "savings",
                "message": "Add your income details to get a personalized savings recommendation.",
                "basis": "No consented income data is available yet.",
            }
        )
    elif surplus > 0:
        suggested_low = round(surplus * 0.6, 2)
        suggested_high = round(surplus * 0.85, 2)
        recs.append(
            {
                "category": "savings",
                "message": (
                    f"Your current average monthly surplus is ₹{surplus:,.0f}. Consider setting a realistic "
                    f"savings target of ₹{suggested_low:,.0f}-₹{suggested_high:,.0f} rather than committing "
                    "the entire surplus."
                ),
                "basis": f"Based on net cash flow of ₹{surplus:,.0f}.",
            }
        )
    else:
        recs.append(
            {
                "category": "savings",
                "message": (
                    "Your recorded expenses currently exceed your income. Consider reviewing your largest "
                    "expense categories before setting a savings target."
                ),
                "basis": f"Net cash flow is currently ₹{surplus:,.0f}.",
            }
        )

    # --- Expense recommendation ---
    if breakdown["categories"]:
        top = breakdown["categories"][0]
        if top["percentage_of_total"] >= 30:
            recs.append(
                {
                    "category": "expenses",
                    "message": (
                        f"{top['category']} is your largest spending category at "
                        f"{top['percentage_of_total']:.0f}% of total expenses. Reviewing this category first "
                        "may have the biggest impact on your cash flow."
                    ),
                    "basis": f"{top['category']} accounts for ₹{top['amount']:,.0f} of total expenses.",
                }
            )

    # --- Borrowing recommendation ---
    active = get_active_consent_categories(db, user_id)
    borrowing = (
        db.query(BorrowingRecord)
        .filter(BorrowingRecord.user_id == user_id)
        .order_by(BorrowingRecord.record_date.desc())
        .first()
        if "borrowing" in active
        else None
    )
    if borrowing is not None and float(borrowing.monthly_repayment) > 0:
        recs.append(
            {
                "category": "borrowing",
                "message": (
                    "Before taking on additional repayment obligations, check whether the added monthly "
                    "amount would significantly reduce your existing savings capacity or emergency buffer."
                ),
                "basis": f"Existing monthly repayment on record: ₹{float(borrowing.monthly_repayment):,.0f}.",
            }
        )
    elif summary["net_cash_flow"] > 0:
        recs.append(
            {
                "category": "borrowing",
                "message": (
                    "You currently have no reported repayment obligations and a positive cash flow. If "
                    "considering credit in the future, review your emergency buffer first."
                ),
                "basis": f"Emergency buffer: {summary['emergency_buffer_months']} months"
                if summary["emergency_buffer_months"] is not None
                else "Emergency buffer has not been calculated yet.",
            }
        )

    # --- Unusual spending recommendation (scikit-learn based, see
    # spending_insights_service) ---
    for finding in spending_insights_service.detect_unusual_spending(db, user_id):
        recs.append(
            {
                "category": "spending_pattern",
                "message": finding["message"],
                "basis": (
                    f"{finding['category']} spend of ₹{finding['amount']:,.0f} in {finding['month']} "
                    f"vs. a {finding['category']} average of ₹{finding['average']:,.0f}/month across your history."
                ),
            }
        )

    return recs


def save_recommendations(db: Session, user_id: str, recs: list[dict]) -> list[Recommendation]:
    # Replace prior recommendations with the freshly computed set so the
    # dashboard always reflects the latest consented data.
    db.query(Recommendation).filter(Recommendation.user_id == user_id).delete()

    saved = []
    for r in recs:
        entry = Recommendation(user_id=user_id, category=r["category"], message=r["message"], basis=r["basis"])
        db.add(entry)
        saved.append(entry)

    db.commit()
    for entry in saved:
        db.refresh(entry)
    return saved
