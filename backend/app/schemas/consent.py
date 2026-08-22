from datetime import datetime

from pydantic import BaseModel, Field

from app.config.thresholds import CONSENT_CATEGORIES


class ConsentCreate(BaseModel):
    data_category: str = Field(description=f"One of: {', '.join(CONSENT_CATEGORIES.keys())}")
    purpose: str | None = Field(default=None, description="Defaults to the standard purpose for this category")


class ConsentOut(BaseModel):
    id: str
    data_category: str
    purpose: str
    is_active: bool
    granted_at: datetime
    revoked_at: datetime | None

    model_config = {"from_attributes": True}
