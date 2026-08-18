import statistics


def calculate_net_cash_flow(total_income, total_expenses):
    """
    Net Cash Flow = Total Income - Total Expenses
    """
    return round(total_income - total_expenses, 2)


def calculate_savings_rate(total_income, total_expenses):
    """
    Savings Rate = (Net Cash Flow / Total Income) * 100

    If income is zero, return None
    to avoid division by zero.
    """

    if total_income == 0:
        return None

    net_cash_flow = total_income - total_expenses

    return round(
        (net_cash_flow / total_income) * 100,
        2
    )


def calculate_expense_ratio(total_income, total_expenses):
    """
    Expense Ratio = (Total Expenses / Total Income) * 100

    If income is zero, return None.
    """

    if total_income == 0:
        return None

    return round(
        (total_expenses / total_income) * 100,
        2
    )


def calculate_emergency_buffer(
    emergency_savings,
    essential_monthly_expenses
):
    """
    Emergency Buffer =
    Emergency Savings / Essential Monthly Expenses
    """

    if essential_monthly_expenses <= 0:
        return None

    return round(
        emergency_savings /
        essential_monthly_expenses,
        2
    )


def calculate_expense_volatility(monthly_expenses):
    """
    Measures how much monthly expenses fluctuate.
    """

    if len(monthly_expenses) < 2:
        return 0

    average_expense = statistics.mean(
        monthly_expenses
    )

    if average_expense == 0:
        return 0

    standard_deviation = statistics.stdev(
        monthly_expenses
    )

    volatility = (
        standard_deviation /
        average_expense
    ) * 100

    return round(volatility, 2)
def classify_financial_health(
    savings_rate,
    expense_ratio,
    emergency_buffer,
    expense_volatility
):
    score = 0

    # Savings Rate
    if savings_rate is not None:
        if savings_rate >= 20:
            score += 30
        elif savings_rate >= 10:
            score += 20
        elif savings_rate >= 5:
            score += 10

    # Expense Ratio
    if expense_ratio is not None:
        if expense_ratio <= 70:
            score += 25
        elif expense_ratio <= 85:
            score += 15
        elif expense_ratio <= 100:
            score += 5

    # Emergency Buffer
    if emergency_buffer is not None:
        if emergency_buffer >= 6:
            score += 25
        elif emergency_buffer >= 3:
            score += 18
        elif emergency_buffer >= 1:
            score += 10

    # Expense Volatility
    if expense_volatility <= 15:
        score += 20
    elif expense_volatility <= 30:
        score += 12
    elif expense_volatility <= 50:
        score += 5

    # Final classification
    if score >= 80:
        return "Healthy"

    elif score >= 60:
        return "Stable"

    elif score >= 40:
        return "Needs Attention"

    else:
        return "High Risk"