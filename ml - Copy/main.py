from app.insights import (
    generate_score_explanation,
    calculate_transaction_summary,
    generate_transaction_insights
)

from app.financial_analysis import (
    calculate_net_cash_flow,
    calculate_savings_rate,
    calculate_expense_ratio,
    calculate_emergency_buffer,
    calculate_expense_volatility,
    classify_financial_health
)

from app.credit_readiness import (
    calculate_credit_readiness,
    get_score_rating
)


# Sample financial data

income = 25000
expenses = 18500

emergency_savings = 20000
essential_expenses = 10000

monthly_expenses = [
    16000,
    17500,
    18000,
    18500,
    19000
]


# Calculations

net_cash_flow = calculate_net_cash_flow(
    income,
    expenses
)

savings_rate = calculate_savings_rate(
    income,
    expenses
)

expense_ratio = calculate_expense_ratio(
    income,
    expenses
)

emergency_buffer = calculate_emergency_buffer(
    emergency_savings,
    essential_expenses
)

expense_volatility = calculate_expense_volatility(
    monthly_expenses
)

financial_health = classify_financial_health(
    savings_rate,
    expense_ratio,
    emergency_buffer,
    expense_volatility
)


# Display results

print("===== FINANCIAL ANALYSIS =====")

print(
    "Total Income:",
    income
)

print(
    "Total Expenses:",
    expenses
)

print(
    "Net Cash Flow:",
    net_cash_flow
)

print(
    "Savings Rate:",
    savings_rate,
    "%"
)

print(
    "Expense Ratio:",
    expense_ratio,
    "%"
)

print(
    "Emergency Buffer:",
    emergency_buffer,
    "months"
)

print(
    "Expense Volatility:",
    expense_volatility,
    "%"
)

print(
    "Financial Health:",
    financial_health
)

credit_data = {

    "monthly_income": 25000,

    "monthly_expenses": 18500,

    "monthly_emi": 2500,

    "monthly_income_history": [
        24000,
        25000,
        25000,
        26000
    ],

    "expense_volatility": 6.47,

    "emergency_buffer_months": 2
}


credit_result = calculate_credit_readiness(
    credit_data
)


credit_rating = get_score_rating(
    credit_result["score"]
)

explanations = generate_score_explanation(
    credit_result["factors"]
)


print("\n===== CREDIT READINESS =====")

print(
    "Credit Readiness Score:",
    credit_result["score"],
    "/ 100"
)

print(
    "Rating:",
    credit_rating
)


print("\n----- Factors -----")

for factor, score in credit_result["factors"].items():

    print(
        factor,
        ":",
        score
    )

print("\n----- Explanations -----")

for item in explanations:

    print(
        f"{item['factor']}: "
        f"{item['status']} - "
        f"{item['explanation']}"
    )

from app.transaction_categorizer import (
    process_csv
)


print("\n===== TRANSACTION ANALYSIS =====")

df = process_csv(
    "sample_data/transactions.csv"
)

print(df)

transaction_summary = (
    calculate_transaction_summary(df)
)

transaction_insights = (
    generate_transaction_insights(
        transaction_summary
    )
)

print("\n===== FINANCIAL INSIGHTS =====")

for insight in transaction_insights:

    print("•", insight)

print("\n===== SPENDING SUMMARY =====")

print(
    "Total Income:",
    transaction_summary["total_income"]
)

print(
    "Total Expenses:",
    transaction_summary["total_expenses"]
)

print(
    "Top Expense Category:",
    transaction_summary[
        "top_expense_category"
    ]
)

print(
    "Top Expense Amount:",
    transaction_summary[
        "top_expense_amount"
    ]
)

print("\n----- Category-wise Expenses -----")

for category, amount in (
    transaction_summary[
        "category_expenses"
    ].items()
):

    print(
        category,
        ":",
        amount
    )