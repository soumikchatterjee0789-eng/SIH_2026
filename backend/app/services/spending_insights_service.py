"""
Unusual Spending Detection - the scikit-learn piece of the Financial
Analytics Engine (see README "Technical Approach": Pandas + NumPy +
Scikit-learn).

Design note (consistent with PRD Section 35 - transparent over opaque):
this module never hides its reasoning behind a bare "trust the model"
score. IsolationForest is used only to flag which category+month
combination is worth a human-readable explanation; the explanation itself
always states the actual numbers (this month's amount vs. the category's
own historical average) so the person can verify it themselves. If a
category doesn't have enough months of history to make that comparison
meaningful, it's skipped rather than guessed at.
"""
from __future__ import annotations

import warnings

import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from app.services.analytics_service import _expense_dataframe
from app.services.consent_service import get_active_consent_categories

# Need at least this many distinct months of history in a category before
# an anomaly call is statistically meaningful at all.
MIN_MONTHS_FOR_DETECTION = 4


def detect_unusual_spending(db: Session, user_id: str, active: set[str] | None = None) -> list[dict]:
    """
    Returns a list of {category, month, amount, average, message} dicts for
    category+month combinations whose spend is a statistical outlier
    relative to that category's own history for this user.

    Only ever compares a user's spending to their own past spending -
    never to other users - so this stays within the consented data for
    this one person (PRD Section 4 - Consent First).
    """
    active = get_active_consent_categories(db, user_id) if active is None else active
    df = _expense_dataframe(db, user_id, active)
    if df.empty:
        return []

    monthly_by_category = df.groupby(["category", "month"], as_index=False)["amount"].sum()

    findings: list[dict] = []
    for category, group in monthly_by_category.groupby("category"):
        group = group.sort_values("month")
        if len(group) < MIN_MONTHS_FOR_DETECTION:
            continue

        amounts = group["amount"].to_numpy().reshape(-1, 1)
        average = float(group["amount"].mean())

        # contamination='auto' with this little data can be noisy; a fixed
        # low contamination keeps it conservative (flag only clear outliers).
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = IsolationForest(n_estimators=100, contamination=0.15, random_state=42)
            labels = model.fit_predict(amounts)  # -1 = outlier, 1 = normal

        latest_idx = group["month"].values.argmax()
        if labels[latest_idx] != -1:
            continue  # most recent month isn't flagged - nothing to surface

        latest_month = group.iloc[latest_idx]["month"]
        latest_amount = float(group.iloc[latest_idx]["amount"])
        if average == 0:
            continue
        pct_diff = round(((latest_amount - average) / average) * 100, 1)
        if pct_diff <= 0:
            continue  # only surface unusually HIGH spend, not unusually low

        findings.append(
            {
                "category": category,
                "month": latest_month,
                "amount": round(latest_amount, 2),
                "average": round(average, 2),
                "message": (
                    f"Your {category} spending in {latest_month} was ₹{latest_amount:,.0f}, "
                    f"about {pct_diff:.0f}% above your usual ₹{average:,.0f} for that category."
                ),
            }
        )

    # Largest deviation first.
    findings.sort(key=lambda f: f["amount"] - f["average"], reverse=True)
    return findings
