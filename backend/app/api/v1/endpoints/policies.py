"""
Policy CRUD scaffolding only.

Editing these values is just data entry in Phase 1 — actually enforcing
them against a proposed AI action is the Policy Engine's job (Phase 4).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.base import get_db
from app.models.policy import Policy
from app.models.user import User
from app.schemas.policy import PolicyRead, PolicyUpdate

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/me", response_model=PolicyRead)
def get_my_policy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Policy:
    policy = db.query(Policy).filter(Policy.user_id == current_user.id).first()
    if policy is None:
        raise NotFoundError("No policy found for this user.")
    return policy


@router.put("/me", response_model=PolicyRead)
def update_my_policy(
    payload: PolicyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Policy:
    policy = db.query(Policy).filter(Policy.user_id == current_user.id).first()
    if policy is None:
        raise NotFoundError("No policy found for this user.")

    for field, value in payload.model_dump().items():
        setattr(policy, field, value)

    db.commit()
    db.refresh(policy)
    return policy
