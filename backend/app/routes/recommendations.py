from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.recommendation import RecommendationOut
from app.utils.response import success_response
from app.utils.deps import get_current_user
from app.services import recommendation_service

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"])


@router.get("")
def get_recommendations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    recs = recommendation_service.generate_recommendations(db, user.id)
    saved = recommendation_service.save_recommendations(db, user.id, recs)
    return success_response([RecommendationOut.model_validate(r).model_dump(mode="json") for r in saved])
