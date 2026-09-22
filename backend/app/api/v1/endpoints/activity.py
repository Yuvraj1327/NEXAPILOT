"""Read-only activity feed. Populated by later phases as events occur."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.activity import Activity
from app.models.user import User
from app.schemas.activity import ActivityRead

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("", response_model=List[ActivityRead])
def list_my_activity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Activity]:
    return (
        db.query(Activity)
        .filter(Activity.user_id == current_user.id)
        .order_by(Activity.created_at.desc())
        .all()
    )
