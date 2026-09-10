"""
AI Financial Context Synthesizer (RAG Pipeline).

Extracts and aggregates real consented financial records for a user into a
privacy-compliant, structured intelligence payload for consumption by
LLMs or the Deep Financial Reasoner.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.transaction import Transaction
from app.models.financial import BorrowingRecord
from app.services import (
    analytics_service,
    credit_readiness_service,
    spending_insights_service,
    consent_service,
)


@dataclass
class FinancialContext:
    user_id: str
    user_name: str
    user_type: str  # "student" | "micro_entrepreneur" | etc.
    active_consents: set[str]
    has_minimum_data: bool
    summary: dict[str, Any]
    cash_flow_series: list[dict[str, Any]]
    expense_breakdown: dict[str, Any]
    savings_analysis: dict[str, Any]
    credit_score: dict[str, Any] | None
    borrowing_snapshot: dict[str, Any] | None
    spending_anomalies: list[dict[str, Any]]
    recent_transactions: list[dict[str, Any]]
    recommendations: list[dict[str, Any]] = field(default_factory=list)

    def to_system_prompt_snippet(self) -> str:
        """Formats the financial context into a high-density, clean markdown prompt block."""
        lines = [
            f"### USER FINANCIAL PROFILE",
            f"- Persona: {self.user_type.replace('_', ' ').title()}",
            f"- Active Consented Categories: {', '.join(sorted(self.active_consents)) if self.active_consents else 'None'}",
        ]

        if not self.has_minimum_data:
            lines.append("- Data Status: Insufficient consented financial records.")
            return "\n".join(lines)

        # Summary figures
        lines.append(f"### FINANCIAL SUMMARY (INR \u20b9)")
        lines.append(f"- Total Recorded Income: \u20b9{self.summary.get('total_income', 0):,.2f}")
        lines.append(f"- Total Recorded Expenses: \u20b9{self.summary.get('total_expenses', 0):,.2f}")
        lines.append(f"- Net Cash Flow: \u20b9{self.summary.get('net_cash_flow', 0):,.2f}")
        sr = self.summary.get('savings_rate')
        lines.append(f"- Savings Rate: {f'{sr:.1f}%' if sr is not None else 'N/A (No income recorded)'}")
        er = self.summary.get('expense_ratio')
        lines.append(f"- Expense Ratio: {f'{er:.1f}%' if er is not None else 'N/A'}")
        lines.append(f"- Health Classification: {self.summary.get('classification', 'NEEDS_ATTENTION')}")

        # Emergency buffer
        eb_months = self.summary.get('emergency_buffer_months')
        eb_status = self.summary.get('emergency_buffer_status')
        lines.append(
            f"- Emergency Buffer: {f'{eb_months:.1f} months ({eb_status})' if eb_months is not None else 'Not established / Unconsented'}"
        )

        # Top Expenses
        categories = self.expense_breakdown.get("categories", [])
        if categories:
            lines.append("### TOP SPENDING CATEGORIES")
            for cat in categories[:5]:
                lines.append(
                    f"  * {cat['category']}: \u20b9{cat['amount']:,.2f} ({cat['percentage_of_total']:.1f}% of expenses)"
                )

        # Credit Readiness Score
        if self.credit_score:
            lines.append("### CREDIT READINESS INDICATOR")
            lines.append(
                f"- Score: {self.credit_score.get('score', 'N/A')}/100 ({self.credit_score.get('rating', 'N/A')})"
            )
            factors = self.credit_score.get("factors", [])
            if factors:
                lines.append("- Driving Score Factors:")
                for f in factors:
                    sign = "+" if f.get("impact", 0) >= 0 else ""
                    lines.append(f"  * {f.get('name')}: {sign}{f.get('impact', 0)} pts ({f.get('explanation', '')})")

        # Borrowing & Debt
        if self.borrowing_snapshot:
            lines.append("### EXISTING DEBT & REPAYMENT OBLIGATIONS")
            lines.append(
                f"- Monthly Repayment: \u20b9{self.borrowing_snapshot.get('monthly_repayment', 0):,.2f}"
            )
            lines.append(
                f"- Total Outstanding: \u20b9{self.borrowing_snapshot.get('total_outstanding', 0):,.2f}"
            )
        else:
            lines.append("### EXISTING DEBT & REPAYMENT: None on record.")

        # Spending Anomalies
        if self.spending_anomalies:
            lines.append("### DETECTED SPENDING ANOMALIES & SURGES")
            for anom in self.spending_anomalies[:3]:
                lines.append(f"  * {anom.get('message', '')} ({anom.get('month', '')})")

        # Recent Transactions
        if self.recent_transactions:
            lines.append("### RECENT TRANSACTION SAMPLES")
            for tx in self.recent_transactions[:5]:
                lines.append(
                    f"  * {tx.get('date')}: {tx.get('type').upper()} \u20b9{tx.get('amount'):,.2f} - {tx.get('title')} [{tx.get('category')}]"
                )

        return "\n".join(lines)


def build_user_financial_context(db: Session, user_id: str) -> FinancialContext:
    user = db.query(User).filter(User.id == user_id).first()
    user_name = user.full_name if user else "Valued User"
    user_type = user.user_type if user else "student"

    active_consents = consent_service.get_active_consent_categories(db, user_id)
    has_min_data = analytics_service.has_minimum_data(db, user_id, active_consents)

    summary = analytics_service.build_financial_summary(db, user_id) if has_min_data else {}
    cash_flow_series = analytics_service.build_cash_flow_series(db, user_id) if has_min_data else []
    expense_breakdown = analytics_service.build_expense_breakdown(db, user_id) if "expenses" in active_consents or "transactions" in active_consents else {"categories": [], "total_expenses": 0.0}
    savings_analysis = analytics_service.build_savings_analysis(db, user_id) if has_min_data else {}

    # Credit readiness
    credit_score_data = None
    curr_score = credit_readiness_service.get_current_score(db, user_id)
    if curr_score:
        credit_score_data = {
            "score": curr_score.score,
            "rating": curr_score.rating,
            "factors": [
                {
                    "name": f.name,
                    "impact": f.impact,
                    "direction": f.direction,
                    "explanation": f.explanation,
                }
                for f in curr_score.factors
            ],
        }
    elif credit_readiness_service.has_sufficient_data_for_score(db, user_id):
        try:
            credit_score_data = credit_readiness_service.calculate_credit_readiness(db, user_id)
        except credit_readiness_service.InsufficientDataError:
            credit_score_data = None

    # Borrowing
    borrowing_snapshot = None
    if "borrowing" in active_consents:
        b_rec = (
            db.query(BorrowingRecord)
            .filter(BorrowingRecord.user_id == user_id)
            .order_by(BorrowingRecord.record_date.desc())
            .first()
        )
        if b_rec:
            borrowing_snapshot = {
                "monthly_repayment": float(b_rec.monthly_repayment),
                "total_outstanding": float(b_rec.total_outstanding),
                "lender_type": b_rec.lender_type,
            }

    # Anomalies
    spending_anomalies = []
    if "expenses" in active_consents or "transactions" in active_consents:
        try:
            spending_anomalies = spending_insights_service.detect_unusual_spending(db, user_id)
        except Exception:
            spending_anomalies = []

    # Recent Transactions
    recent_txs = []
    if "transactions" in active_consents:
        tx_rows = (
            db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .limit(10)
            .all()
        )
        recent_txs = [
            {
                "date": t.transaction_date.isoformat(),
                "type": t.type,
                "amount": float(t.amount),
                "title": t.description,
                "category": t.category,
            }
            for t in tx_rows
        ]

    return FinancialContext(
        user_id=user_id,
        user_name=user_name,
        user_type=user_type,
        active_consents=active_consents,
        has_minimum_data=has_min_data,
        summary=summary,
        cash_flow_series=cash_flow_series,
        expense_breakdown=expense_breakdown,
        savings_analysis=savings_analysis,
        credit_score=credit_score_data,
        borrowing_snapshot=borrowing_snapshot,
        spending_anomalies=spending_anomalies,
        recent_transactions=recent_txs,
    )
