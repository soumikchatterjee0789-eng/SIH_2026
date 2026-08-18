import json

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

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

from app.transaction_categorizer import (
    process_csv
)

from app.insights import (
    calculate_transaction_summary,
    generate_transaction_insights
)


# ==========================================
# FASTAPI APP
# ==========================================

app = FastAPI(
    title="Financial Health Assistant - P3 AI/ML API",
    version="1.0.0"
)


# ==========================================
# REQUEST MODELS
# ==========================================

class FinancialHealthRequest(BaseModel):

    total_income: float
    total_expenses: float
    emergency_savings: float
    essential_monthly_expenses: float
    monthly_expenses: List[float]


class CreditReadinessRequest(BaseModel):

    monthly_income: float
    monthly_expenses: float
    monthly_emi: float
    monthly_income_history: List[float]
    expense_volatility: float
    emergency_buffer_months: float


# ==========================================
# HOME
# ==========================================

@app.get("/")
def home():

    return {
        "success": True,
        "message": "P3 AI/ML API is running"
    }


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy"
    }


# ==========================================
# FINANCIAL HEALTH
# ==========================================

@app.post("/financial-health")
def financial_health(
    data: FinancialHealthRequest
):

    net_cash_flow = calculate_net_cash_flow(
        data.total_income,
        data.total_expenses
    )

    savings_rate = calculate_savings_rate(
        data.total_income,
        data.total_expenses
    )

    expense_ratio = calculate_expense_ratio(
        data.total_income,
        data.total_expenses
    )

    emergency_buffer = calculate_emergency_buffer(
        data.emergency_savings,
        data.essential_monthly_expenses
    )

    expense_volatility = calculate_expense_volatility(
        data.monthly_expenses
    )

    health = classify_financial_health(
        savings_rate,
        expense_ratio,
        emergency_buffer,
        expense_volatility
    )

    return {

        "success": True,

        "financial_analysis": {

            "net_cash_flow": net_cash_flow,

            "savings_rate": savings_rate,

            "expense_ratio": expense_ratio,

            "emergency_buffer_months":
                emergency_buffer,

            "expense_volatility":
                expense_volatility
        },

        "financial_health": health
    }


# ==========================================
# CREDIT READINESS
# ==========================================

@app.post("/credit-readiness")
def credit_readiness(
    data: CreditReadinessRequest
):

    credit_data = {

        "monthly_income":
            data.monthly_income,

        "monthly_expenses":
            data.monthly_expenses,

        "monthly_emi":
            data.monthly_emi,

        "monthly_income_history":
            data.monthly_income_history,

        "expense_volatility":
            data.expense_volatility,

        "emergency_buffer_months":
            data.emergency_buffer_months
    }

    result = calculate_credit_readiness(
        credit_data
    )

    rating = get_score_rating(
        result["score"]
    )

    return {

        "success": True,

        "credit_readiness_score":
            result["score"],

        "rating":
            rating,

        "factors":
            result["factors"],

        "weights":
            result["weights"]
    }


# ==========================================
# TRANSACTION ANALYSIS
# ==========================================

@app.get("/transactions/analyze")
def analyze_transactions():

    file_path = "sample_data/transactions.csv"

    # Read and categorize transactions
    df = process_csv(file_path)

    # Calculate spending summary
    summary = calculate_transaction_summary(df)

    # Generate financial insights
    insights = generate_transaction_insights(
        summary
    )

    # Convert DataFrame into JSON-safe data
    transactions = json.loads(
        df.to_json(
            orient="records"
        )
    )

    # Convert ALL NumPy values in summary
    # into normal Python JSON values
    summary = json.loads(
        json.dumps(
            summary,
            default=lambda value:
                value.item()
                if hasattr(value, "item")
                else str(value)
        )
    )

    return {
        "success": True,
        "summary": summary,
        "insights": insights,
        "transactions": transactions
    }