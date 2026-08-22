from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

FREQUENCIES = {"monthly", "weekly", "biweekly", "one_time", "irregular"}

EXPENSE_CATEGORIES = {
    "Food", "Rent/Hostel", "Education", "Transport", "Utilities",
    "Healthcare", "Business", "Entertainment", "Shopping", "Other",
}


class IncomeCreate(BaseModel):
    source: str = Field(min_length=1, max_length=255)
    amount: float = Field(gt=0)
    frequency: str
    record_date: date

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        if v not in FREQUENCIES:
            raise ValueError(f"frequency must be one of {sorted(FREQUENCIES)}")
        return v


class IncomeUpdate(BaseModel):
    source: str | None = None
    amount: float | None = Field(default=None, gt=0)
    frequency: str | None = None
    record_date: date | None = None
    correction_reason: str | None = None


class IncomeOut(BaseModel):
    id: str
    source: str
    amount: float
    frequency: str
    record_date: date
    is_corrected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseCreate(BaseModel):
    category: str
    amount: float = Field(gt=0)
    frequency: str
    record_date: date

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        if v not in FREQUENCIES:
            raise ValueError(f"frequency must be one of {sorted(FREQUENCIES)}")
        return v


class ExpenseUpdate(BaseModel):
    category: str | None = None
    amount: float | None = Field(default=None, gt=0)
    frequency: str | None = None
    record_date: date | None = None
    correction_reason: str | None = None


class ExpenseOut(BaseModel):
    id: str
    category: str
    amount: float
    frequency: str
    record_date: date
    is_corrected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SavingsCreate(BaseModel):
    current_savings: float = Field(ge=0)
    monthly_savings: float = Field(ge=0)
    emergency_savings: float = Field(ge=0)
    record_date: date


class SavingsOut(BaseModel):
    id: str
    current_savings: float
    monthly_savings: float
    emergency_savings: float
    record_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class BorrowingCreate(BaseModel):
    """Optional - only ever submitted if the user has granted 'borrowing' consent."""
    existing_loan_amount: float = Field(ge=0, default=0)
    monthly_repayment: float = Field(ge=0, default=0)
    remaining_period_months: int = Field(ge=0, default=0)
    record_date: date


class BorrowingOut(BaseModel):
    id: str
    existing_loan_amount: float
    monthly_repayment: float
    remaining_period_months: int
    record_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class FinancialDataBundle(BaseModel):
    """Aggregated read model returned by GET /api/financial-data"""
    income: list[IncomeOut]
    expenses: list[ExpenseOut]
    savings: list[SavingsOut]
    borrowing: list[BorrowingOut]
