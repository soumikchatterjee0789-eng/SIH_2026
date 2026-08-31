from datetime import datetime

from pydantic import BaseModel


class ScoreFactorOut(BaseModel):
    name: str
    impact: float
    direction: str
    explanation: str

    model_config = {"from_attributes": True}


class CreditReadinessOut(BaseModel):
    score: int
    rating: str
    disclaimer: str
    factors: list[ScoreFactorOut]
    calculated_at: datetime


class CreditReadinessChangeOut(BaseModel):
    previous_score: int | None
    new_score: int
    change: int | None
    reason: str
