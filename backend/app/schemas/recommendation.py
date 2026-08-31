from datetime import datetime

from pydantic import BaseModel


class RecommendationOut(BaseModel):
    id: str
    category: str
    message: str
    basis: str
    created_at: datetime

    model_config = {"from_attributes": True}
