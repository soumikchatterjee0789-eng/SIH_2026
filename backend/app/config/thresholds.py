"""
Central configuration for financial-health classification thresholds and
credit-readiness scoring weights.

PRD Section 13 explicitly requires:
    "Do not hard-code unexplained thresholds throughout the application.
     Create a central configuration: FINANCIAL_HEALTH_THRESHOLDS"

PRD Section 14 explicitly requires the credit-readiness factor weights to
be configurable defaults, not fixed constants scattered across the code.

Any service that needs a threshold or weight MUST import it from here.
"""

# ---------------------------------------------------------------------------
# Financial Health Classification (PRD Section 13)
# ---------------------------------------------------------------------------
# Classification is driven by savings_rate (%) and expense_ratio (%).
# Buckets are evaluated top-down; the first matching bucket wins.
FINANCIAL_HEALTH_THRESHOLDS = {
    "HEALTHY": {"min_savings_rate": 20, "max_expense_ratio": 80},
    "STABLE": {"min_savings_rate": 10, "max_expense_ratio": 90},
    "NEEDS_ATTENTION": {"min_savings_rate": 0, "max_expense_ratio": 100},
    "HIGH_RISK": {"min_savings_rate": float("-inf"), "max_expense_ratio": float("inf")},
}

# Order matters: evaluated top-to-bottom, first match wins.
FINANCIAL_HEALTH_ORDER = ["HEALTHY", "STABLE", "NEEDS_ATTENTION", "HIGH_RISK"]

# Minimum number of income + expense records required before the system
# will attempt to classify financial health at all (PRD Section 28 - Empty
# States: never show a fabricated result when there isn't enough data).
MIN_RECORDS_FOR_FINANCIAL_HEALTH = 1

# ---------------------------------------------------------------------------
# Emergency Buffer classification (in months of essential expenses)
# ---------------------------------------------------------------------------
EMERGENCY_BUFFER_THRESHOLDS = {
    "STRONG": 6,
    "ADEQUATE": 3,
    "LOW": 1,
    # below LOW => "CRITICAL"
}

# ---------------------------------------------------------------------------
# Credit Readiness Engine (PRD Section 14)
# ---------------------------------------------------------------------------
# Weights MUST sum to 100. These are example defaults per the PRD table and
# can be changed by ops/config without touching scoring logic.
CREDIT_READINESS_WEIGHTS = {
    "income_stability": 25,
    "cash_flow_health": 20,
    "savings_capacity": 20,
    "expense_stability": 15,
    "repayment_burden": 10,
    "emergency_buffer": 10,
}

assert sum(CREDIT_READINESS_WEIGHTS.values()) == 100, "Credit readiness weights must sum to 100"

# Minimum consented data required before a credit-readiness score can be
# produced at all. Below this, the API must return INSUFFICIENT_DATA
# (PRD Section 28) rather than a fabricated score of 0.
MIN_MONTHS_FOR_CREDIT_READINESS = 1
MIN_INCOME_RECORDS_FOR_CREDIT_READINESS = 1

# Rating bands for the final 0-100 score (PRD Section 16 example: "Moderate")
CREDIT_READINESS_RATING_BANDS = [
    (80, 100, "Strong"),
    (60, 79, "Moderate"),
    (40, 59, "Developing"),
    (0, 39, "Needs Improvement"),
]

# ---------------------------------------------------------------------------
# Sensitive attributes that must NEVER influence scoring (PRD Section 15).
# Kept here as a documented allow-list guard; the scoring engine validates
# against this list defensively even though the data model never stores them.
# ---------------------------------------------------------------------------
PROHIBITED_SCORING_ATTRIBUTES = {
    "religion", "caste", "race", "gender", "political_affiliation",
    "health_condition", "personal_beliefs", "ethnicity", "disability",
    "marital_status", "sexual_orientation",
}

# ---------------------------------------------------------------------------
# Consent data categories (PRD Section 8)
# ---------------------------------------------------------------------------
CONSENT_CATEGORIES = {
    "income": "Cash-flow analysis",
    "expenses": "Financial health analysis",
    "transactions": "Spending analysis",
    "savings": "Savings capacity",
    "borrowing": "Credit readiness",
}
