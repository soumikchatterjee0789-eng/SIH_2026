from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class TransactionOut(BaseModel):
    id: str
    transaction_date: date
    description: str
    amount: float
    type: str
    category: str
    is_corrected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionUpdate(BaseModel):
    description: str | None = None
    amount: float | None = Field(default=None, gt=0)
    category: str | None = None
    type: str | None = None
    correction_reason: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str | None) -> str | None:
        if v is not None and v not in {"income", "expense"}:
            raise ValueError("type must be 'income' or 'expense'")
        return v


class CSVRowPreview(BaseModel):
    row_number: int
    date: str | None = None
    description: str | None = None
    amount: str | None = None
    type: str | None = None
    category: str | None = None
    valid: bool
    errors: list[str] = []


class CSVUploadPreview(BaseModel):
    """Returned on preview (confirm=false). Nothing is stored yet."""
    batch_token: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[CSVRowPreview]


class CSVUploadResult(BaseModel):
    """Returned once confirm=true and valid rows are actually stored."""
    inserted_count: int
    skipped_count: int
    source_batch_id: str
