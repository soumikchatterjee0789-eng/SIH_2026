def generate_score_explanation(factors):

    explanations = []

    for factor, score in factors.items():

        readable_name = (
            factor
            .replace("_", " ")
            .title()
        )

        if score >= 80:

            explanations.append({
                "factor": readable_name,
                "score": score,
                "status": "Positive",
                "explanation":
                    f"{readable_name} is relatively strong."
            })

        elif score >= 50:

            explanations.append({
                "factor": readable_name,
                "score": score,
                "status": "Moderate",
                "explanation":
                    f"{readable_name} is at a moderate level."
            })

        else:

            explanations.append({
                "factor": readable_name,
                "score": score,
                "status": "Needs Attention",
                "explanation":
                    f"{readable_name} may need improvement."
            })

    return explanations

def calculate_transaction_summary(df):

    # Total income
    total_income = df[
        df["type"] == "income"
    ]["amount"].sum()

    # Total expenses
    total_expenses = df[
        df["type"] == "expense"
    ]["amount"].sum()

    # Expense transactions only
    expense_df = df[
        df["type"] == "expense"
    ]

    # Category-wise expense
    category_expenses = (
        expense_df
        .groupby("category")["amount"]
        .sum()
        .sort_values(
            ascending=False
        )
    )

    # Top expense category
    if len(category_expenses) > 0:

        top_category = (
            category_expenses.index[0]
        )

        top_category_amount = (
            category_expenses.iloc[0]
        )

    else:

        top_category = None
        top_category_amount = 0

    return {

        "total_income":
            round(total_income, 2),

        "total_expenses":
            round(total_expenses, 2),

        "category_expenses":
            category_expenses.to_dict(),

        "top_expense_category":
            top_category,

        "top_expense_amount":
            round(
                top_category_amount,
                2
            )
    }

def generate_transaction_insights(summary):

    insights = []

    total_income = summary["total_income"]
    total_expenses = summary["total_expenses"]

    top_category = summary["top_expense_category"]
    top_amount = summary["top_expense_amount"]

    # -----------------------------
    # Savings insight
    # -----------------------------

    net_savings = total_income - total_expenses

    if total_income > 0:

        savings_rate = (
            net_savings / total_income
        ) * 100

        savings_rate = round(
            savings_rate,
            2
        )

        insights.append(
            f"Your analyzed savings rate is "
            f"{savings_rate}%."
        )

    # -----------------------------
    # Top expense insight
    # -----------------------------

    if top_category is not None:

        insights.append(
            f"Your largest expense category "
            f"is {top_category}, "
            f"with spending of ₹{top_amount}."
        )

    # -----------------------------
    # Total expense insight
    # -----------------------------

    insights.append(
        f"Your total analyzed expenses "
        f"are ₹{total_expenses}."
    )

    # -----------------------------
    # Net savings insight
    # -----------------------------

    if net_savings > 0:

        insights.append(
            f"Your analyzed income exceeds "
            f"expenses by ₹{net_savings}."
        )

    elif net_savings < 0:

        insights.append(
            f"Your analyzed expenses exceed "
            f"income by ₹{abs(net_savings)}."
        )

    else:

        insights.append(
            "Your analyzed income and "
            "expenses are equal."
        )

    return insights