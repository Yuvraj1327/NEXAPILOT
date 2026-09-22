"""
/api/v1/policy — standalone Policy Engine access (Phase 4).

Distinct from /api/v1/policies (Phase 1's CRUD for a user's own Policy
row — reading/editing max amount, daily limit, allowed lists, etc.). This
router is about *evaluating* a hypothetical action against that policy:

  POST /api/v1/policy/evaluate — runs the exact same Risk Check -> Policy
    Check -> PASS/REJECT pipeline app/api/v1/endpoints/ai.py runs for a
    real Claude TRANSACTION_PLAN, but for a hypothetical action supplied
    directly, so it can be exercised (or used by a future frontend "what
    would happen if I did this?" preview) without going through Claude.

  GET /api/v1/policy/usage — how much of today's daily limit is already
    committed, so a frontend can show remaining headroom.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.blockchain.service import best_effort_native_balance
from app.core.exceptions import NotFoundError
from app.db.base import get_db
from app.models.policy import Policy
from app.models.user import User
from app.models.wallet import Wallet
from app.policy_engine.engine import determine_transaction_status, evaluate_policy, get_already_spent_today
from app.risk.engine import assess_risk
from app.schemas.policy import PolicyEvaluationRequest, PolicyEvaluationResponse, PolicyUsage

router = APIRouter(prefix="/policy", tags=["policy"])


def _get_policy_and_wallet(current_user: User, db: Session) -> tuple[Policy, Wallet]:
    policy = db.query(Policy).filter(Policy.user_id == current_user.id).first()
    if policy is None:
        raise NotFoundError("No policy found for this user.")
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == current_user.id)
        .order_by(Wallet.is_primary.desc(), Wallet.created_at.asc())
        .first()
    )
    if wallet is None:
        raise NotFoundError("Connect a wallet before evaluating a policy.")
    return policy, wallet


@router.post("/evaluate", response_model=PolicyEvaluationResponse)
def evaluate(
    payload: PolicyEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PolicyEvaluationResponse:
    policy, wallet = _get_policy_and_wallet(current_user, db)

    wallet_balance = best_effort_native_balance(wallet.address)
    risk_assessment = assess_risk(
        operation=payload.operation,
        amount=payload.amount,
        protocol=payload.protocol,
        action_type=payload.action_type,
        wallet_balance=wallet_balance,
    )
    already_spent_today = get_already_spent_today(db, current_user.id)
    policy_decision = evaluate_policy(
        policy=policy,
        operation=payload.operation,
        amount=payload.amount,
        protocol=payload.protocol,
        action_type=payload.action_type,
        risk_level=risk_assessment.risk_level,
        already_spent_today=already_spent_today,
    )

    return PolicyEvaluationResponse(
        risk_level=risk_assessment.risk_level,
        risk_score=risk_assessment.score,
        policy_decision=policy_decision,
        final_status=determine_transaction_status(policy_decision),
    )


@router.get("/usage", response_model=PolicyUsage)
def usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PolicyUsage:
    policy = db.query(Policy).filter(Policy.user_id == current_user.id).first()
    if policy is None:
        raise NotFoundError("No policy found for this user.")

    spent_today = get_already_spent_today(db, current_user.id)
    remaining = policy.daily_limit - spent_today
    return PolicyUsage(
        daily_limit=policy.daily_limit,
        spent_today=spent_today,
        remaining_today=remaining if remaining > 0 else 0,
    )
