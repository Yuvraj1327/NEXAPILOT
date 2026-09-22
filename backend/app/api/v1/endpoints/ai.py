"""
POST /api/v1/ai/query — the NexaPilot AI Copilot endpoint.

Turns a natural-language request into a validated structured action (see
app/schemas/ai.py). For a TRANSACTION_PLAN, this creates a Transaction row
and immediately runs it through the deterministic Phase 4 safety layer,
in order:

  1. Risk Engine (app/risk/engine.py) -- scores the proposed action
     LOW/MEDIUM/HIGH from fixed, explainable factors. Not influenced by
     Claude's own `risk_notes`, which is advisory-only text for the user.
  2. Policy Engine (app/policy_engine/engine.py) -- checks the action (plus
     that risk level) against the user's own stored Policy: max amount,
     daily limit, allowed protocols/actions, max risk level.

The Transaction's `status` lands on exactly one of RISK_REJECTED,
POLICY_REJECTED, AWAITING_APPROVAL, or APPROVED as a direct, deterministic
result of those two engines -- never on anything Claude decided. Nothing
here signs or broadcasts a transaction; APPROVED/AWAITING_APPROVAL rows
still require the user's own explicit action through the Phase 2
/blockchain/transactions/* flow before anything reaches the chain.
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.service import run_ai_query
from app.ai.tools import ToolContext
from app.api.deps import get_current_user
from app.blockchain.service import best_effort_native_balance
from app.core.exceptions import NotFoundError
from app.db.base import get_db
from app.models.activity import Activity
from app.models.enums import ActivityType, TransactionStatus
from app.models.policy import Policy
from app.models.transaction import Transaction
from app.models.user import User
from app.models.wallet import Wallet
from app.policy_engine.engine import determine_transaction_status, evaluate_policy, get_already_spent_today
from app.risk.engine import assess_risk
from app.schemas.ai import AIIntent, AIQueryRequest, AIQueryResponse

logger = logging.getLogger("nexapilot.ai")

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/query", response_model=AIQueryResponse)
def query_ai(
    payload: AIQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIQueryResponse:
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == current_user.id)
        .order_by(Wallet.is_primary.desc(), Wallet.created_at.asc())
        .first()
    )
    if wallet is None:
        raise NotFoundError("Connect a wallet before using the AI Copilot.")

    policy = db.query(Policy).filter(Policy.user_id == current_user.id).first()
    if policy is None:
        raise NotFoundError("No policy found for this user.")

    ctx = ToolContext(user=current_user, wallet=wallet, policy=policy, db=db)
    action, tools_used = run_ai_query(ctx=ctx, message=payload.message)

    transaction_id = None
    transaction_status = None
    risk_level = None
    if action.intent == AIIntent.TRANSACTION_PLAN:
        proposed = action.proposed_transaction
        tx_row = Transaction(
            user_id=current_user.id,
            wallet_id=wallet.id,
            action_type=proposed.action_type or proposed.operation.upper(),
            protocol=proposed.protocol,
            token_in="MON",
            amount_in=proposed.amount,
            status=TransactionStatus.PENDING,
            chain=wallet.chain,
            target_contract=proposed.target_contract,
            raw_ai_action=action.model_dump(mode="json"),
        )
        db.add(tx_row)
        db.flush()  # assigns tx_row.id without ending the transaction, so
        # the daily-limit lookup below can exclude this not-yet-decided row

        # --- Phase 4 safety layer: Risk Check -> Policy Check -> PASS/REJECT ---
        wallet_balance = best_effort_native_balance(wallet.address)
        risk_assessment = assess_risk(
            operation=proposed.operation,
            amount=proposed.amount,
            protocol=proposed.protocol,
            action_type=proposed.action_type,
            wallet_balance=wallet_balance,
        )
        already_spent_today = get_already_spent_today(db, current_user.id, exclude_transaction_id=tx_row.id)
        policy_decision = evaluate_policy(
            policy=policy,
            operation=proposed.operation,
            amount=proposed.amount,
            protocol=proposed.protocol,
            action_type=proposed.action_type,
            risk_level=risk_assessment.risk_level,
            already_spent_today=already_spent_today,
        )

        tx_row.risk_level = risk_assessment.risk_level
        tx_row.risk_explanation = risk_assessment.model_dump(mode="json")
        tx_row.policy_decision = policy_decision.model_dump(mode="json")
        tx_row.status = determine_transaction_status(policy_decision)

        db.commit()
        db.refresh(tx_row)
        transaction_id = str(tx_row.id)
        transaction_status = tx_row.status
        risk_level = tx_row.risk_level

    db.add(
        Activity(
            user_id=current_user.id,
            type=ActivityType.RECOMMENDATION,
            title=action.summary,
            description=action.explanation[:1024],
            related_transaction_id=tx_row.id if transaction_id else None,
            activity_metadata={
                "intent": action.intent.value,
                "tools_used": tools_used,
                "transaction_id": transaction_id,
            },
        )
    )
    db.commit()

    return AIQueryResponse(
        action=action,
        transaction_id=transaction_id,
        tools_used=tools_used,
        transaction_status=transaction_status,
        risk_level=risk_level,
    )
