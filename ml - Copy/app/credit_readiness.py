# Credit Readiness Score Configuration

WEIGHTS = {
    "income_stability": 0.25,
    "cash_flow_health": 0.20,
    "savings_capacity": 0.20,
    "expense_stability": 0.15,
    "repayment_burden": 0.10,
    "emergency_buffer": 0.10
}


def calculate_income_stability(monthly_income_history):
    """
    Calculates income stability from historical
    monthly income values.
    """

    if len(monthly_income_history) < 2:
        return 50

    average_income = (
        sum(monthly_income_history)
        / len(monthly_income_history)
    )

    if average_income == 0:
        return 0

    variation = sum(
        abs(income - average_income)
        / average_income
        for income in monthly_income_history
    ) / len(monthly_income_history)

    score = 100 - (variation * 100)

    return round(
        max(0, min(100, score)),
        2
    )


def calculate_cash_flow_health(
    monthly_income,
    monthly_expenses
):
    """
    Measures the health of monthly cash flow.
    """

    if monthly_income <= 0:
        return 0

    surplus_ratio = (
        monthly_income - monthly_expenses
    ) / monthly_income

    score = surplus_ratio * 100

    return round(
        max(0, min(100, score)),
        2
    )


def calculate_savings_capacity(
    monthly_income,
    monthly_expenses
):
    """
    Estimates savings capacity based on
    monthly surplus.
    """

    if monthly_income <= 0:
        return 0

    savings_rate = (
        (monthly_income - monthly_expenses)
        / monthly_income
    ) * 100

    score = (
        savings_rate / 30
    ) * 100

    return round(
        max(0, min(100, score)),
        2
    )


def calculate_expense_stability(
    expense_volatility
):
    """
    Lower expense volatility produces
    a higher stability score.
    """

    score = 100 - expense_volatility

    return round(
        max(0, min(100, score)),
        2
    )


def calculate_repayment_burden(
    monthly_emi,
    monthly_income
):
    """
    Lower EMI-to-income ratio produces
    a higher score.
    """

    if monthly_income <= 0:
        return 0

    repayment_ratio = (
        monthly_emi / monthly_income
    )

    score = 100 - (
        repayment_ratio * 100
    )

    return round(
        max(0, min(100, score)),
        2
    )


def calculate_emergency_buffer_score(
    buffer_months
):
    """
    Converts emergency buffer months
    into a 0-100 score.
    """

    if buffer_months is None:
        return 0

    score = (
        buffer_months / 6
    ) * 100

    return round(
        max(0, min(100, score)),
        2
    )


def calculate_credit_readiness(data):

    monthly_income = data.get(
        "monthly_income",
        0
    )

    monthly_expenses = data.get(
        "monthly_expenses",
        0
    )

    monthly_emi = data.get(
        "monthly_emi",
        0
    )

    monthly_income_history = data.get(
        "monthly_income_history",
        []
    )

    expense_volatility = data.get(
        "expense_volatility",
        0
    )

    emergency_buffer_months = data.get(
        "emergency_buffer_months",
        0
    )

    factors = {

        "income_stability":
            calculate_income_stability(
                monthly_income_history
            ),

        "cash_flow_health":
            calculate_cash_flow_health(
                monthly_income,
                monthly_expenses
            ),

        "savings_capacity":
            calculate_savings_capacity(
                monthly_income,
                monthly_expenses
            ),

        "expense_stability":
            calculate_expense_stability(
                expense_volatility
            ),

        "repayment_burden":
            calculate_repayment_burden(
                monthly_emi,
                monthly_income
            ),

        "emergency_buffer":
            calculate_emergency_buffer_score(
                emergency_buffer_months
            )
    }

    weighted_score = sum(
        factors[name] * WEIGHTS[name]
        for name in factors
    )

    final_score = round(
        max(0, min(100, weighted_score))
    )

    return {
        "score": final_score,
        "factors": factors,
        "weights": WEIGHTS
    }


def get_score_rating(score):

    if score >= 80:
        return "Strong"

    elif score >= 60:
        return "Moderate"

    elif score >= 40:
        return "Needs Improvement"

    else:
        return "Low"