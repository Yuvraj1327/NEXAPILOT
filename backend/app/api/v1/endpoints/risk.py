"""
POST /api/v1/risk/assess — standalone Risk Engine access.

Lets a caller (frontend, tester, or curious user) score a hypothetical
action without going through Claude at all, using the exact same
deterministic app.risk.engine.assess_risk function the AI flow uses for a
real TRANSACTION_PLAN (app/api/v1/endpoints/ai.py) — one engine, two
entry points, never two copies of the risk logic.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.blockchain.service import best_effort_native_balance
from app.core.exceptions import NotFoundError
from app.db.base import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.risk.engine import assess_risk
from app.schemas.risk import RiskAssessment, RiskAssessmentRequest

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/assess", response_model=RiskAssessment)
def assess(
    payload: RiskAssessmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RiskAssessment:
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == current_user.id)
        .order_by(Wallet.is_primary.desc(), Wallet.created_at.asc())
        .first()
    )
    if wallet is None:
        raise NotFoundError("Connect a wallet before requesting a risk assessment.")

    wallet_balance = best_effort_native_balance(wallet.address)

    return assess_risk(
        operation=payload.operation,
        amount=payload.amount,
        protocol=payload.protocol,
        action_type=payload.action_type,
        wallet_balance=wallet_balance,
    )
