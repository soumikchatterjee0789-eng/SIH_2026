"""
Deep Financial Intelligence & Reasoning Engine.

Autonomous, zero-dependency financial reasoner that operates over consented
financial records to provide structured, explainable, step-by-step advisory
responses with mathematical precision.

Handles 15+ intent categories with context-aware, data-driven responses.
"""
from __future__ import annotations

import re
from typing import Any
from app.services.ai_engine.context_builder import FinancialContext

INSUFFICIENT_DATA_GUIDANCE = (
    "### 🛡 Insufficient Consented Data\n\n"
    "I need a bit more consented financial activity before I can run a deep analysis on that topic.\n\n"
    "**Quick steps to unlock full AI advisory:**\n"
    "1. **Grant Consents**: Open the **Consent Manager** tab and enable *Income*, *Expenses*, and *Transactions*.\n"
    "2. **Add Data**: Record your monthly income/expenses in the **Data** tab, or upload a CSV statement.\n"
    "3. **Explore Instantly**: Click **'Load Demo Data'** from the Home screen to explore with realistic mock data."
)


def _fmt(val: float | int | None) -> str:
    if val is None:
        return "\u20b90"
    return f"\u20b9{abs(val):,.0f}"


def _pct(val: float | int | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:.1f}%"


def _extract_number(text: str) -> float | None:
    # Match patterns like 5000, 5,000, ₹5000, Rs 5000
    cleaned = text.replace(",", "")
    match = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)", cleaned, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _has_keywords(q: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in the question (as whole words or substrings)."""
    return any(k in q for k in keywords)


class DeepFinancialReasoner:
    """Comprehensive deterministic financial reasoning engine."""

    def reason(self, context: FinancialContext, question: str) -> tuple[str, bool, list[str]]:
        """
        Analyzes the user question against the financial context.
        Returns: (markdown_answer, used_insufficient_data_fallback, suggested_followups)
        """
        q = question.lower().strip()

        # Handle unconsented or zero-data edge cases
        if not context.has_minimum_data:
            return INSUFFICIENT_DATA_GUIDANCE, True, [
                "How do I load demo data?",
                "What data consents are needed?",
                "How is financial health calculated?",
            ]

        # === Greeting / casual ===
        if _has_keywords(q, ["hello", "hi ", "hey", "good morning", "good evening", "namaste", "sup", "howdy"]) and len(q) < 30:
            return self._handle_greeting(context, q)

        # === Thank you ===
        if _has_keywords(q, ["thank", "thanks", "thx", "appreciate", "helpful"]):
            return self._handle_thanks(context, q)

        # === What can you do / help ===
        if _has_keywords(q, ["what can you", "help me", "what do you", "how can you", "what are you", "who are you", "features"]):
            return self._handle_capabilities(context, q)

        # === Credit Readiness Score & Factor Breakdown ===
        if _has_keywords(q, ["score", "credit readiness", "credit score", "rating", "readiness",
                              "cibil", "improve score", "points", "72", "credit rating"]):
            return self._analyze_credit_score(context, q)

        # === Spending Analysis, Leaks & Category Breakdown ===
        if _has_keywords(q, ["spend", "spending", "expense", "expenses", "category",
                              "where am i", "leak", "cut down", "cost", "where does",
                              "most money", "going", "outflow", "high cost",
                              "reduce expense", "reduce spending", "cut expense"]):
            return self._analyze_spending(context, q)

        # === Savings, Budgeting, Surplus & Reserve Goals ===
        if _has_keywords(q, ["save", "saving", "savings", "surplus", "buffer", "emergency",
                              "reserve", "50/30/20", "budget", "how much can i",
                              "put aside", "set aside", "piggy", "deposit"]):
            return self._analyze_savings(context, q)

        # === Loans, Debt, EMI & Repayment Capacity ===
        if _has_keywords(q, ["loan", "borrow", "borrowing", "debt", "emi", "repayment",
                              "afford", "credit card", "interest", "installment",
                              "repay", "mortgage", "lending"]):
            return self._analyze_borrowing(context, q)

        # === Decrease/Reduce Debt (specific intent) ===
        if _has_keywords(q, ["decrease debt", "reduce debt", "pay off debt",
                              "get out of debt", "debt free", "clear debt",
                              "pay down", "settle debt", "debt reduction"]):
            return self._analyze_debt_reduction(context, q)

        # === Income Analysis ===
        if _has_keywords(q, ["income", "salary", "earn", "earning", "stipend",
                              "allowance", "inflow", "revenue", "monthly income",
                              "how much do i make", "how much i earn"]):
            return self._analyze_income(context, q)

        # === Financial Health / Overview ===
        if _has_keywords(q, ["health", "financial health", "overall", "summary",
                              "overview", "status", "how am i doing",
                              "financial status", "my finances", "financial situation",
                              "diagnosis", "checkup"]):
            return self._generate_holistic_roadmap(context, q)

        # === Cash Flow Specific ===
        if _has_keywords(q, ["cash flow", "cashflow", "surplus", "deficit",
                              "positive", "negative", "net flow", "monthly flow",
                              "inflow vs outflow", "in vs out"]):
            return self._analyze_cashflow(context, q)

        # === Transactions / Recent Activity ===
        if _has_keywords(q, ["transaction", "recent", "latest", "activity",
                              "history", "last few", "what did i", "purchase"]):
            return self._analyze_transactions(context, q)

        # === Tips / Advice / Suggestions ===
        if _has_keywords(q, ["tip", "tips", "advice", "suggest", "recommendation",
                              "what should i", "how do i", "guide", "strategy",
                              "plan", "roadmap", "steps", "improve", "better",
                              "optimize", "boost"]):
            return self._generate_financial_tips(context, q)

        # === Comparison / Benchmark ===
        if _has_keywords(q, ["compared", "benchmark", "average", "ideal",
                              "normal", "standard", "peer", "similar", "healthy range",
                              "good enough"]):
            return self._analyze_benchmarks(context, q)

        # === Default: Holistic Roadmap ===
        return self._generate_holistic_roadmap(context, q)

    # ------------------------------------------------------------------
    # GREETING
    # ------------------------------------------------------------------
    def _handle_greeting(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        name = ctx.user_name or "there"
        score = ctx.credit_score.get("score", "N/A") if ctx.credit_score else "In Progress"
        surplus = ctx.summary.get("net_cash_flow", 0)
        sr = ctx.summary.get("savings_rate")

        lines = [
            f"### 👋 Hello, **{name}**!\n",
            f"Great to see you. Here's a quick snapshot of your financial health:\n",
            f"- **Credit Readiness Score**: **{score}/100**",
            f"- **Monthly Surplus**: {'+' if surplus >= 0 else '-'}{_fmt(surplus)}",
            f"- **Savings Rate**: {_pct(sr)}\n",
            f"What would you like to dive into? I can analyze your spending, savings capacity, credit score, debt feasibility, or give you a full financial roadmap.",
        ]
        return "\n".join(lines), False, [
            "Why is my credit readiness score what it is?",
            "Where am I spending the most?",
            "How can I save more every month?",
        ]

    # ------------------------------------------------------------------
    # THANKS
    # ------------------------------------------------------------------
    def _handle_thanks(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        return (
            "### 🙏 You're Welcome!\n\n"
            "I'm here anytime you need financial guidance. Your financial health matters, "
            "and every small step toward better money habits makes a big difference.\n\n"
            "Feel free to ask me anything else!",
            False,
            [
                "Give me a full financial summary",
                "How can I improve my credit readiness?",
                "What are the best savings tips for me?",
            ],
        )

    # ------------------------------------------------------------------
    # CAPABILITIES
    # ------------------------------------------------------------------
    def _handle_capabilities(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        persona = "student & young adult" if ctx.user_type == "student" else "micro-entrepreneur"
        lines = [
            f"### 🤖 WiseGuardian AI Financial Advisor\n",
            f"I'm your dedicated financial advisor tailored for **{persona}** profiles. Here's what I can help with:\n",
            f"#### 📊 Analysis & Insights:",
            f"- **Credit Readiness Score** — deep-dive into your 6-factor score with improvement roadmap",
            f"- **Spending Breakdown** — category-wise expense analysis with anomaly detection",
            f"- **Savings Capacity** — feasibility analysis for any savings goal you set",
            f"- **Cash Flow Trends** — monthly income vs expense comparisons\n",
            f"#### 💳 Debt & Borrowing:",
            f"- **EMI Affordability** — check if you can safely take on a specific EMI",
            f"- **Debt Reduction** — strategies to pay down existing obligations",
            f"- **Borrowing Safety** — prudential checks before taking any loan\n",
            f"#### 💡 Planning:",
            f"- **Financial Tips** — personalized actionable advice for your situation",
            f"- **Benchmark Comparison** — how your numbers compare to healthy standards",
            f"- **Full Health Roadmap** — 360° financial diagnosis with action steps\n",
            f"**Just ask in plain English!** For example: *\"Can I afford a ₹5,000 EMI?\"* or *\"Where is my money going?\"*",
        ]
        return "\n".join(lines), False, [
            "Give me my full financial summary",
            "Where am I spending the most?",
            "Can I afford an EMI of ₹5,000?",
        ]

    # ------------------------------------------------------------------
    # CREDIT SCORE
    # ------------------------------------------------------------------
    def _analyze_credit_score(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        cs = ctx.credit_score
        if not cs:
            return (
                "### 📊 Credit Readiness Assessment\n\n"
                "Your Credit Readiness Score requires at least two periods of consented income and transaction records "
                "to evaluate stability. Once recorded, your score will be computed transparently across 6 distinct risk and liquidity factors.",
                False,
                ["Where am I spending the most?", "How can I improve my savings rate?"],
            )

        score = cs.get("score", 0)
        rating = cs.get("rating", "Building Phase")
        factors = cs.get("factors", [])

        positives = sorted([f for f in factors if f.get("impact", 0) >= 0],
                           key=lambda x: x.get("impact", 0), reverse=True)
        negatives = sorted([f for f in factors if f.get("impact", 0) < 0 or
                           "varies" in f.get("explanation", "").lower() or
                           "low" in f.get("explanation", "").lower()],
                           key=lambda x: x.get("impact", 0))

        lines = [
            f"### 🛡 Credit Readiness Deep-Dive: **{score}/100** ({rating.upper()})\n",
            f"Your score indicates **{rating}**. Unlike traditional black-box credit bureaus, "
            f"WiseGuardian evaluates your profile transparently across **{len(factors)} explainable pillars**:\n",
        ]

        if positives:
            lines.append("#### 🟢 Key Positive Score Drivers:")
            for f in positives[:3]:
                lines.append(f"- **{f['name']}** (+{f['impact']} pts): {f['explanation']}")
            lines.append("")

        if negatives:
            lines.append("#### 🟡 Key Improvement Opportunities:")
            for f in negatives[:3]:
                lines.append(f"- **{f['name']}** ({f['impact']} pts): {f['explanation']}")
            lines.append("")

        # Actionable score improvement roadmap
        target_score = min(100, score + 12)
        lines.append(f"#### 🎯 Strategic Roadmap to Reach {target_score}/100:")

        eb = ctx.summary.get("emergency_buffer_months") or 0
        sr = ctx.summary.get("savings_rate") or 0
        if eb < 3:
            lines.append("1. **Strengthen Emergency Reserves**: Building a 3-month essential buffer can boost your reserve score factor by **+5 to +10 points**.")
        if sr < 20:
            lines.append("2. **Consistent Monthly Surplus**: Retaining at least 15-20% of net monthly inflow improves your Savings Capacity factor.")
        lines.append("3. **Expense Predictability**: Keeping monthly non-essential expenses within a steady bracket optimizes the Expense Stability metric.")

        followups = [
            "Where am I spending the most?",
            f"Can I afford to save {_fmt((ctx.summary.get('net_cash_flow', 0) or 0) * 0.5)} monthly?",
            "What is my emergency buffer status?",
        ]
        return "\n".join(lines), False, followups

    # ------------------------------------------------------------------
    # SPENDING
    # ------------------------------------------------------------------
    def _analyze_spending(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        breakdown = ctx.expense_breakdown
        categories = breakdown.get("categories", [])
        total_exp = breakdown.get("total_expenses", 0)
        income = ctx.summary.get("total_income", 0)

        if not categories:
            return (
                "### 💸 Spending Analysis\n\n"
                "No categorized expense records were found. Add expense entries or upload transaction data to view category allocations.",
                False,
                ["How is my overall financial health?", "How can I budget better?"],
            )

        top_cat = categories[0]
        top_pct = top_cat.get("percentage_of_total", 0)

        lines = [
            f"### 💸 Expense Breakdown & Spending Allocation\n",
            f"Your total recorded monthly expenses stand at **{_fmt(total_exp)}** "
            f"against an income of **{_fmt(income)}**.\n",
            f"#### 🏷 Category Distribution:",
        ]

        for cat in categories[:6]:
            bar_filled = int(cat.get("percentage_of_total", 0) / 5)
            bar = "█" * bar_filled + "░" * (20 - bar_filled)
            lines.append(
                f"- **{cat['category']}**: {_fmt(cat['amount'])} "
                f"({cat['percentage_of_total']:.1f}%) {bar}"
            )

        lines.append("")
        if top_pct >= 35:
            savings_if_cut = top_cat['amount'] * 0.12
            lines.append(
                f"> **💡 Concentration Alert**: **{top_cat['category']}** consumes **{top_pct:.0f}%** of your total outflows. "
                f"Trimming this single category by 10-15% would free up approx **{_fmt(savings_if_cut)}/month** "
                f"into your liquidity reserves."
            )

        if ctx.spending_anomalies:
            lines.append("\n#### ⚠️ Detected Spending Anomalies:")
            for anom in ctx.spending_anomalies[:3]:
                lines.append(f"- {anom.get('message', '')}")

        lines.append("\n#### 🛠 Actionable Recommendations:")
        lines.append(f"1. **Audit Top Category**: Review `{top_cat['category']}` for recurring subscriptions or bulk spends you can trim.")
        if income > 0:
            essential_ratio = (total_exp / income) * 100
            lines.append(f"2. **50/30/20 Rule**: Your expenses are **{essential_ratio:.0f}%** of income. Target keeping needs under 50%, wants under 30%, savings at 20%+.")
        lines.append(f"3. **Weekly Spending Cap**: Set a weekly limit of **{_fmt(total_exp / 4.3)}** to prevent month-end cash crunches.")

        followups = [
            "How can I save more every month?",
            "What is my current Credit Readiness Score?",
            "Can I afford a new loan or EMI?",
        ]
        return "\n".join(lines), False, followups

    # ------------------------------------------------------------------
    # SAVINGS
    # ------------------------------------------------------------------
    def _analyze_savings(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        summary = ctx.summary
        surplus = summary.get("net_cash_flow", 0.0)
        income = summary.get("total_income", 0.0)
        expenses = summary.get("total_expenses", 0.0)
        savings_rate = summary.get("savings_rate")
        eb_months = summary.get("emergency_buffer_months")

        asked_amount = _extract_number(q)

        lines = [
            f"### 💰 Savings Capacity & Liquidity Assessment\n",
            f"- **Monthly Income**: {_fmt(income)}",
            f"- **Monthly Expenses**: {_fmt(expenses)}",
            f"- **Net Monthly Cash Flow**: {'+' if surplus >= 0 else '-'}{_fmt(surplus)}",
            f"- **Current Savings Rate**: {_pct(savings_rate)}",
            f"- **Emergency Buffer**: {f'{eb_months:.1f} months' if eb_months is not None else 'Not established'}\n",
        ]

        if asked_amount is not None and asked_amount > 0:
            lines.append(f"#### 🎯 Feasibility for Saving {_fmt(asked_amount)} / Month:")
            if surplus <= 0:
                lines.append(
                    f"❌ **Currently High Risk**: Your expenses ({_fmt(expenses)}) exceed your income ({_fmt(income)}), "
                    f"resulting in a deficit of **{_fmt(abs(surplus))}**. Committing to a fixed savings goal of {_fmt(asked_amount)} "
                    "would cause cash flow stress. Focus on stabilizing non-essential outflows first."
                )
            elif asked_amount <= (surplus * 0.75):
                lines.append(
                    f"✅ **Highly Achievable**: With an average surplus of **{_fmt(surplus)}**, committing **{_fmt(asked_amount)}/month** "
                    f"leaves a healthy safety buffer of **{_fmt(surplus - asked_amount)}** for unforeseen day-to-day fluctuations."
                )
                lines.append(f"\n**12-month projection**: You'd accumulate **{_fmt(asked_amount * 12)}** in savings.")
            elif asked_amount <= surplus:
                lines.append(
                    f"⚠️ **Tight Fit**: Saving {_fmt(asked_amount)} consumes nearly your entire surplus ({_fmt(surplus)}). "
                    f"A more realistic starting commitment is **{_fmt(surplus * 0.7)}/month** to avoid cash crunches."
                )
            else:
                safe = round(surplus * 0.7, -2) if surplus > 0 else 0
                lines.append(
                    f"❌ **Exceeds Surplus**: Your current average monthly surplus is **{_fmt(surplus)}**. "
                    f"A target of **{_fmt(safe)}/month** is mathematically sustainable."
                )
            lines.append("")
        else:
            if surplus > 0:
                recommended_save = round(surplus * 0.7, -2) if surplus >= 200 else round(surplus * 0.5)
                lines.append(
                    f"#### 📈 Recommended Action Plan:\n"
                    f"- **Recommended Monthly Savings Goal**: **{_fmt(recommended_save)}** (approx 70% of your net surplus).\n"
                    f"- **12-Month Projected Growth**: You could accumulate **{_fmt(recommended_save * 12)}** in annual reserves.\n"
                    f"- **Emergency Fund Target**: Build **{_fmt(expenses * 3)}** (3 months of expenses) before any discretionary investing."
                )
            else:
                lines.append(
                    "#### ⚠️ Cash Flow Caution:\n"
                    "Your cash flow is currently negative or near zero. Prioritize:\n"
                    "1. Identify and cut the **top discretionary expense** category\n"
                    "2. Target breakeven cash flow first before setting savings targets\n"
                    "3. Even ₹500/month saved consistently builds a crucial safety net"
                )

        followups = [
            f"Can I save {_fmt(max((surplus or 10000) * 0.5, 500))} per month?",
            "Where am I spending the most?",
            "How does my savings rate affect my credit score?",
        ]
        return "\n".join(lines), False, followups

    # ------------------------------------------------------------------
    # BORROWING (loans, EMI, can I afford)
    # ------------------------------------------------------------------
    def _analyze_borrowing(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        summary = ctx.summary
        income = summary.get("total_income", 0.0)
        expenses = summary.get("total_expenses", 0.0)
        surplus = summary.get("net_cash_flow", 0.0)
        eb_months = summary.get("emergency_buffer_months")
        borrowing = ctx.borrowing_snapshot

        asked_emi = _extract_number(q)
        max_safe_emi = round(income * 0.20, -2) if income > 0 else 0.0

        lines = [
            f"### 💳 Borrowing & Repayment Capacity Evaluation\n",
            f"WiseGuardian assesses debt feasibility strictly through **cash flow safety** and **repayment capacity**.\n",
        ]

        # Show existing debt info
        if borrowing and borrowing.get("monthly_repayment", 0) > 0:
            lines.append("#### 📋 Your Current Debt Status:")
            lines.append(f"- **Existing Monthly EMI / Repayment**: {_fmt(borrowing['monthly_repayment'])}")
            lines.append(f"- **Total Outstanding Debt**: {_fmt(borrowing['total_outstanding'])}")
            if borrowing.get("lender_type"):
                lines.append(f"- **Lender Type**: {borrowing['lender_type']}")
            remaining_capacity = max(0, max_safe_emi - borrowing['monthly_repayment'])
            lines.append(f"- **Remaining Safe Borrowing Capacity**: {_fmt(remaining_capacity)}/month\n")
        else:
            lines.append("#### 📋 Current Debt Status: **No existing debts on record** ✅\n")

        lines.append(f"#### 🛡 Key Prudential Safeguards:")
        lines.append(f"- **Maximum Safe Monthly Debt Cap (20% Income Rule)**: **{_fmt(max_safe_emi)}/month**")
        lines.append(f"- **Current Monthly Income**: **{_fmt(income)}**")
        lines.append(f"- **Current Net Monthly Surplus**: **{'+' if surplus >= 0 else '-'}{_fmt(surplus)}**")
        lines.append(f"- **Emergency Reserve Buffer**: {f'{eb_months:.1f} months' if eb_months is not None else '0 months (not established)'}\n")

        if asked_emi and asked_emi > 0:
            lines.append(f"#### 🔍 Assessment for EMI of {_fmt(asked_emi)}/month:")
            existing_emi = borrowing.get("monthly_repayment", 0) if borrowing else 0
            total_debt_load = existing_emi + asked_emi

            if surplus <= 0:
                lines.append(
                    f"⛔ **High Risk**: With negative cash flow ({_fmt(surplus)}), taking on an additional {_fmt(asked_emi)}/month "
                    "obligation will quickly trigger debt distress. Focus on building positive surplus first."
                )
            elif asked_emi > surplus:
                lines.append(
                    f"⛔ **Unsafe**: The requested EMI of {_fmt(asked_emi)} exceeds your monthly cash surplus of {_fmt(surplus)}. "
                    f"Maximum sustainable EMI: **{_fmt(surplus * 0.7)}**."
                )
            elif total_debt_load > max_safe_emi:
                lines.append(
                    f"⚠️ **Caution - High Burden**: While {_fmt(asked_emi)} fits within your surplus, "
                    f"your total debt load ({_fmt(total_debt_load)}) would exceed 20% of income. "
                    f"Ensure you maintain a minimum 3-month emergency buffer before proceeding."
                )
            else:
                after_emi_surplus = surplus - asked_emi
                lines.append(
                    f"✅ **Feasible & Safe**: An EMI of {_fmt(asked_emi)} is within your monthly surplus ({_fmt(surplus)}) "
                    f"and complies with the 20% prudent debt-to-income threshold ({_fmt(max_safe_emi)}).\n"
                    f"- **Remaining surplus after EMI**: {_fmt(after_emi_surplus)}/month"
                )
        else:
            lines.append(
                "#### 💡 Senior Advisor Guidance Before Borrowing:\n"
                "1. **Maintain 3-Month Buffer**: Never deplete emergency savings for loan down-payments.\n"
                "2. **Cap Repayments**: Total repayments across all loans should stay below 15-20% of net monthly income.\n"
                "3. **Avoid High-Cost Short-Term Credit**: Steer clear of unregulated quick-loan apps.\n"
                "4. **Compare Interest Rates**: Bank loans (10-14%) are far cheaper than app-based lending (24-36%)."
            )

        followups = [
            f"Can I afford an EMI of {_fmt(max_safe_emi * 0.75)}?",
            "What is my Credit Readiness Score?",
            "How can I increase my monthly surplus?",
        ]
        return "\n".join(lines), False, followups

    # ------------------------------------------------------------------
    # DEBT REDUCTION (specific: how to decrease/reduce/pay off debt)
    # ------------------------------------------------------------------
    def _analyze_debt_reduction(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        summary = ctx.summary
        income = summary.get("total_income", 0.0)
        surplus = summary.get("net_cash_flow", 0.0)
        borrowing = ctx.borrowing_snapshot

        lines = [
            f"### 📉 Debt Reduction Strategy\n",
        ]

        if borrowing and borrowing.get("total_outstanding", 0) > 0:
            outstanding = borrowing["total_outstanding"]
            monthly_emi = borrowing["monthly_repayment"]
            months_to_clear = outstanding / monthly_emi if monthly_emi > 0 else float('inf')

            lines.append(f"#### Your Current Debt Profile:")
            lines.append(f"- **Total Outstanding**: {_fmt(outstanding)}")
            lines.append(f"- **Monthly Repayment**: {_fmt(monthly_emi)}")
            lines.append(f"- **Estimated Months to Clear** (at current rate): **{months_to_clear:.0f} months**")
            lines.append(f"- **Available Surplus**: {_fmt(surplus)}\n")

            if surplus > 0:
                extra_payment = round(surplus * 0.4, -2)
                accelerated_months = outstanding / (monthly_emi + extra_payment) if (monthly_emi + extra_payment) > 0 else months_to_clear
                lines.append(f"#### 🚀 Accelerated Payoff Plan:")
                lines.append(f"1. **Add {_fmt(extra_payment)}/month** extra to your EMI (40% of surplus)")
                lines.append(f"2. This reduces payoff time from **{months_to_clear:.0f}** to **{accelerated_months:.0f} months**")
                lines.append(f"3. You'd save significant interest over the loan tenure\n")

            lines.append(f"#### 🛠 5-Step Debt Reduction Roadmap:")
            lines.append(f"1. **List All Debts**: Organize by interest rate (highest first)")
            lines.append(f"2. **Avalanche Method**: Pay minimums on all, throw extra cash at the highest-interest debt")
            lines.append(f"3. **Cut One Expense**: Identify one discretionary category to reduce by 20%")
            lines.append(f"4. **No New Debt**: Avoid taking additional loans until current ones are under control")
            lines.append(f"5. **Emergency Fund First**: Keep at least 1 month's expenses liquid even while paying down debt")
        else:
            lines.append(
                "Great news! **You currently have no recorded debt obligations.** 🎉\n\n"
                "To maintain this healthy position:\n"
                "1. **Avoid impulsive borrowing** — always run an affordability check first\n"
                "2. **Build an emergency fund** before considering any credit\n"
                "3. **If you do borrow**, keep total EMIs below 20% of your monthly income"
            )

        followups = [
            "What is my Credit Readiness Score?",
            "How can I save more each month?",
            "Where am I spending the most?",
        ]
        return "\n".join(lines), False, followups

    # ------------------------------------------------------------------
    # INCOME ANALYSIS
    # ------------------------------------------------------------------
    def _analyze_income(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        summary = ctx.summary
        income = summary.get("total_income", 0.0)
        expenses = summary.get("total_expenses", 0.0)
        surplus = summary.get("net_cash_flow", 0.0)
        sr = summary.get("savings_rate")

        lines = [
            f"### 💵 Income Analysis\n",
            f"#### Your Income Profile:",
            f"- **Total Monthly Income**: **{_fmt(income)}**",
            f"- **Total Monthly Expenses**: {_fmt(expenses)}",
            f"- **Net Surplus**: {'+' if surplus >= 0 else '-'}{_fmt(surplus)}",
            f"- **Savings Rate**: {_pct(sr)}\n",
        ]

        if income > 0:
            lines.append("#### 📊 Income Utilization Breakdown:")
            if expenses > 0:
                exp_pct = (expenses / income) * 100
                sav_pct = ((income - expenses) / income) * 100 if surplus >= 0 else 0
                lines.append(f"- **{exp_pct:.0f}%** goes to expenses ({_fmt(expenses)})")
                if surplus >= 0:
                    lines.append(f"- **{sav_pct:.0f}%** is available for savings & reserves ({_fmt(surplus)})")
                else:
                    lines.append(f"- ⚠️ You're spending **{exp_pct:.0f}%** of income — that's **{_fmt(abs(surplus))} over budget**")

            lines.append(f"\n#### 💡 Income Optimization Tips:")
            if ctx.user_type == "student":
                lines.append("1. **Track Every Source**: Stipends, part-time work, freelancing — log them all for accurate analysis")
                lines.append("2. **Monthly Allocation**: On income day, immediately set aside 20% for savings before spending")
                lines.append("3. **Skill-Based Earning**: Consider tutoring, freelancing, or campus jobs to boost income")
            else:
                lines.append("1. **Separate Business & Personal**: Transfer a fixed 'salary' to personal accounts monthly")
                lines.append("2. **Invoice Promptly**: Delayed invoicing = delayed cash flow")
                lines.append("3. **Diversify Revenue**: Add a second income stream to smooth seasonal fluctuations")
        else:
            lines.append("No income records found. Add your income sources in the **Data** tab to unlock full analysis.")

        followups = [
            "Where am I spending the most?",
            "How much can I save each month?",
            "What is my Credit Readiness Score?",
        ]
        return "\n".join(lines), False, followups

    # ------------------------------------------------------------------
    # CASH FLOW
    # ------------------------------------------------------------------
    def _analyze_cashflow(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        summary = ctx.summary
        income = summary.get("total_income", 0.0)
        expenses = summary.get("total_expenses", 0.0)
        surplus = summary.get("net_cash_flow", 0.0)
        classification = summary.get("classification", "Unknown")

        lines = [
            f"### 📊 Cash Flow Analysis\n",
            f"| Metric | Amount |",
            f"| :--- | :--- |",
            f"| **Total Inflow** | {_fmt(income)} |",
            f"| **Total Outflow** | {_fmt(expenses)} |",
            f"| **Net Cash Flow** | {'+' if surplus >= 0 else '-'}{_fmt(surplus)} |",
            f"| **Health Status** | **{classification}** |\n",
        ]

        if surplus > 0:
            lines.append(f"✅ **Positive Cash Flow**: You retain **{_fmt(surplus)}** monthly after all expenses.")
            lines.append(f"\nThis surplus can be strategically allocated:")
            lines.append(f"- **70%** ({_fmt(surplus * 0.7)}) → Savings & emergency fund")
            lines.append(f"- **20%** ({_fmt(surplus * 0.2)}) → Short-term goals")
            lines.append(f"- **10%** ({_fmt(surplus * 0.1)}) → Discretionary / reward spending")
        elif surplus == 0:
            lines.append("⚠️ **Breakeven**: Your income exactly covers expenses. Any unexpected cost would cause a deficit.")
        else:
            lines.append(f"🔴 **Negative Cash Flow**: You're spending **{_fmt(abs(surplus))}** more than you earn monthly.")
            lines.append(f"\n**Immediate Action Required:**")
            lines.append(f"1. Review your top expense categories for cuts")
            lines.append(f"2. Target reducing outflow by at least {_fmt(abs(surplus) + 1000)} to reach safety")

        # Show trend if available
        if ctx.cash_flow_series:
            lines.append(f"\n#### 📈 Recent Monthly Trends:")
            for entry in ctx.cash_flow_series[-3:]:
                month = entry.get("month", "")
                inc = entry.get("income", 0)
                exp = entry.get("expenses", 0)
                net = inc - exp
                emoji = "✅" if net >= 0 else "🔴"
                lines.append(f"- **{month}**: {_fmt(inc)} in / {_fmt(exp)} out = {emoji} {'+' if net >= 0 else '-'}{_fmt(net)}")

        followups = [
            "Where am I spending the most?",
            "How can I save more each month?",
            "What is my Credit Readiness Score?",
        ]
        return "\n".join(lines), False, followups

    # ------------------------------------------------------------------
    # TRANSACTIONS
    # ------------------------------------------------------------------
    def _analyze_transactions(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        txs = ctx.recent_transactions

        if not txs:
            return (
                "### 📋 Recent Transactions\n\n"
                "No transaction records found. You can add them manually in the **Data & Transactions** tab "
                "or upload a CSV bank statement.",
                False,
                ["How do I add transactions?", "Give me my financial summary"],
            )

        lines = [
            f"### 📋 Recent Transaction Activity\n",
            f"Here are your latest **{len(txs)}** recorded transactions:\n",
            f"| Date | Type | Description | Category | Amount |",
            f"| :--- | :--- | :--- | :--- | :--- |",
        ]

        total_income_recent = 0
        total_expense_recent = 0
        for tx in txs[:10]:
            t_type = tx.get("type", "").upper()
            amt = tx.get("amount", 0)
            if t_type == "INCOME":
                total_income_recent += amt
            else:
                total_expense_recent += amt
            lines.append(
                f"| {tx.get('date', 'N/A')} | {t_type} | {tx.get('title', 'N/A')} | "
                f"{tx.get('category', 'N/A')} | {_fmt(amt)} |"
            )

        lines.append(f"\n**Summary of recent records**: {_fmt(total_income_recent)} inflow, {_fmt(total_expense_recent)} outflow")

        followups = [
            "Where am I spending the most?",
            "Give me a full financial health summary",
            "How can I save more?",
        ]
        return "\n".join(lines), False, followups

    # ------------------------------------------------------------------
    # FINANCIAL TIPS
    # ------------------------------------------------------------------
    def _generate_financial_tips(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        summary = ctx.summary
        income = summary.get("total_income", 0.0)
        expenses = summary.get("total_expenses", 0.0)
        surplus = summary.get("net_cash_flow", 0.0)
        sr = summary.get("savings_rate") or 0
        eb = summary.get("emergency_buffer_months") or 0

        persona = ctx.user_type

        lines = [
            f"### 💡 Personalized Financial Tips\n",
            f"Based on your current financial profile, here are **actionable recommendations**:\n",
        ]

        # Priority 1: Emergency fund
        if eb < 3:
            lines.append(f"#### 1. 🚨 Build Emergency Fund (Priority: HIGH)")
            lines.append(f"   - **Current buffer**: {eb:.1f} months → **Target**: 3 months ({_fmt(expenses * 3)})")
            lines.append(f"   - Set aside **{_fmt(min(surplus * 0.5, expenses))}**/month until you reach the target\n")

        # Priority 2: Savings rate
        if sr < 20:
            lines.append(f"#### 2. 📈 Improve Savings Rate")
            lines.append(f"   - **Current**: {sr:.1f}% → **Target**: 20%+")
            target_savings = income * 0.2
            lines.append(f"   - You need to save **{_fmt(target_savings)}**/month to hit 20%")
            gap = target_savings - max(0, surplus)
            if gap > 0:
                lines.append(f"   - This requires reducing expenses by **{_fmt(gap)}**\n")
            else:
                lines.append(f"   - ✅ Your surplus already supports this! Just commit to saving it.\n")

        # Priority 3: Spending control
        top_cats = ctx.expense_breakdown.get("categories", [])
        if top_cats:
            top = top_cats[0]
            lines.append(f"#### 3. 🎯 Audit Your Top Expense: {top['category']}")
            lines.append(f"   - Currently **{_fmt(top['amount'])}**/month ({top['percentage_of_total']:.0f}% of total)")
            lines.append(f"   - Cutting this by 15% saves **{_fmt(top['amount'] * 0.15)}**/month = **{_fmt(top['amount'] * 0.15 * 12)}**/year\n")

        # Persona-specific tips
        if persona == "student":
            lines.append("#### 🎓 Student-Specific Tips:")
            lines.append("- Use student discounts aggressively (transport, food, software)")
            lines.append("- Cook 3-4 meals/week at home to save 30-40% on food expenses")
            lines.append("- Track daily micro-expenses (chai, snacks) — they add up to ₹2,000-5,000/month")
            lines.append("- Start a ₹500/month RD (Recurring Deposit) to build savings discipline")
        else:
            lines.append("#### 💼 Entrepreneur-Specific Tips:")
            lines.append("- Separate business and personal bank accounts completely")
            lines.append("- Invoice immediately on delivery — don't delay receivables")
            lines.append("- Maintain 3 months of operating expenses in a liquid business fund")
            lines.append("- Reinvest profits into revenue-generating activities, not lifestyle upgrades")

        followups = [
            "What is my Credit Readiness Score?",
            "Can I afford to save ₹5,000/month?",
            "Show me my spending breakdown",
        ]
        return "\n".join(lines), False, followups

    # ------------------------------------------------------------------
    # BENCHMARKS / COMPARISON
    # ------------------------------------------------------------------
    def _analyze_benchmarks(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        summary = ctx.summary
        income = summary.get("total_income", 0.0)
        expenses = summary.get("total_expenses", 0.0)
        surplus = summary.get("net_cash_flow", 0.0)
        sr = summary.get("savings_rate") or 0
        eb = summary.get("emergency_buffer_months") or 0
        score = ctx.credit_score.get("score", 0) if ctx.credit_score else 0

        exp_ratio = (expenses / income * 100) if income > 0 else 0

        def status(val, good_threshold, bad_threshold, higher_is_better=True):
            if higher_is_better:
                if val >= good_threshold: return "✅ Excellent"
                if val >= bad_threshold: return "⚠️ Needs Work"
                return "🔴 Critical"
            else:
                if val <= good_threshold: return "✅ Excellent"
                if val <= bad_threshold: return "⚠️ Needs Work"
                return "🔴 Critical"

        lines = [
            f"### 📊 Financial Health Benchmarks\n",
            f"How your numbers compare to healthy financial standards:\n",
            f"| Metric | Your Value | Healthy Target | Status |",
            f"| :--- | :--- | :--- | :--- |",
            f"| **Savings Rate** | {sr:.1f}% | ≥ 20% | {status(sr, 20, 10)} |",
            f"| **Expense Ratio** | {exp_ratio:.0f}% | ≤ 80% | {status(exp_ratio, 70, 80, False)} |",
            f"| **Emergency Buffer** | {eb:.1f} months | ≥ 3 months | {status(eb, 3, 1)} |",
            f"| **Credit Readiness** | {score}/100 | ≥ 70 | {status(score, 70, 50)} |",
            f"| **Cash Flow** | {'+' if surplus >= 0 else '-'}{_fmt(surplus)} | Positive | {'✅ Excellent' if surplus > 0 else '🔴 Critical'} |",
        ]

        # Count how many are in good shape
        good_count = sum([
            sr >= 20,
            exp_ratio <= 80,
            eb >= 3,
            score >= 70,
            surplus > 0,
        ])

        lines.append(f"\n**Overall Assessment**: **{good_count}/5** metrics in healthy range.")
        if good_count == 5:
            lines.append("🌟 **Outstanding!** Your financial discipline is exemplary.")
        elif good_count >= 3:
            lines.append("👍 **Good progress!** Focus on the red/yellow metrics to reach full financial strength.")
        else:
            lines.append("⚡ **Action needed.** Several key metrics need attention. Start with the most critical ones first.")

        followups = [
            "How can I improve my savings rate?",
            "What tips do you have for me?",
            "How do I build my emergency fund?",
        ]
        return "\n".join(lines), False, followups

    # ------------------------------------------------------------------
    # HOLISTIC ROADMAP (fallback for unmatched questions)
    # ------------------------------------------------------------------
    def _generate_holistic_roadmap(self, ctx: FinancialContext, q: str) -> tuple[str, bool, list[str]]:
        summary = ctx.summary
        income = summary.get("total_income", 0.0)
        expenses = summary.get("total_expenses", 0.0)
        surplus = summary.get("net_cash_flow", 0.0)
        sr = summary.get("savings_rate")
        cs = ctx.credit_score
        score_str = f"{cs['score']}/100 ({cs['rating']})" if cs else "In Progress"

        persona_title = "🎓 Student & Young Adult Strategy" if ctx.user_type == "student" else "💼 Micro-Entrepreneur Strategy"

        lines = [
            f"### 🛡 WiseGuardian AI Financial Intelligence Summary\n",
            f"Hello **{ctx.user_name}**! Here is your 360-degree financial health diagnosis:\n",
            f"| Metric | Current Status | Healthy Benchmark |",
            f"| :--- | :--- | :--- |",
            f"| **Monthly Inflow** | {_fmt(income)} | Consistent Baseline |",
            f"| **Monthly Outflows** | {_fmt(expenses)} | < 80% of Inflow |",
            f"| **Net Cash Flow** | {'+' if surplus >= 0 else '-'}{_fmt(surplus)} | Positive Surplus |",
            f"| **Savings Rate** | {_pct(sr)} | ≥ 20% |",
            f"| **Credit Readiness** | **{score_str}** | ≥ 70 (Strong) |",
            f"",
            f"#### {persona_title}:",
        ]

        if ctx.user_type == "student":
            lines.append("1. **Stipend / Allowance Pacing**: Allocate funds on day 1 of the month to protect tuition & rent.")
            lines.append("2. **Micro-Savings Habit**: Save even ₹500–₹1,000 monthly to establish a proven savings track record.")
            lines.append("3. **Credit Readiness Building**: A stable cash flow builds creditworthiness without credit card debt.")
        else:
            lines.append("1. **Operating Buffer**: Maintain at least 3 months of essential overhead in a liquid reserve.")
            lines.append("2. **Revenue Smoothing**: Transfer a fixed 'salary' to personal accounts to smooth out seasonal spikes.")
            lines.append("3. **Prudent Debt Leverage**: Borrow only for revenue-generating assets when cash flow is demonstrably positive.")

        # Add specific insights based on their data
        if surplus < 0:
            lines.append(f"\n> ⚠️ **Alert**: Your expenses exceed income by **{_fmt(abs(surplus))}**. This needs immediate attention.")
        elif sr is not None and sr < 10:
            lines.append(f"\n> 💡 **Tip**: Your savings rate is {sr:.1f}%. Aim for 20%+ by reducing your top expense category.")

        followups = [
            "Why is my Credit Readiness Score what it is?",
            "Where am I spending the most?",
            "Can I afford to save more each month?",
            "Give me personalized financial tips",
        ]
        return "\n".join(lines), False, followups
