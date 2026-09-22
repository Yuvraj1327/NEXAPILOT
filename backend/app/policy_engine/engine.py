"""
Deterministic Policy Engine (Phase 4).

Evaluates a proposed action -- plus its already-computed Risk Engine
verdict -- against the user's own stored Policy row (app/models/policy.py).
Nothing here is influenced by Claude; `risk_level` is passed in as a plain
value already produced by app.risk.engine.assess_risk, and every other
input is the proposed action's own fields plus the user's policy and
transaction history. Every rule is checked independently and every result
returned, so PASS/REJECT is always fully explainable.

"Reject unsafe or unauthorized actions before transaction execution"
(project rule): this module's `evaluate_policy` is the single place that
turns a Risk Check's verdict plus every policy rule into one PASS/REJECT
decision, reused identically by the AI flow (app/api/v1/endpoints/ai.py)
and the standalone what-if endpoint (app/api/v1/endpoints/policy.py) --
one source of truth, not two copies of the same logic.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import RiskLevel, TransactionStatus
from app.models.policy import Policy
from app.models.transaction import Transaction
from app.schemas.policy import PolicyCheckResult, PolicyDecision

_RISK_RANK = {RiskLevel.LOW: 0, RiskLevel.MEDIUM: 1, RiskLevel.HIGH: 2}

# Transaction statuses that represent spend already "committed" toward the
# user's daily limit. A freshly AI-proposed PENDING row hasn't been
# risk/policy checked yet, and a rejected/failed one never happened --
# neither should count against today's limit.
_COUNTS_TOWARD_DAILY_LIMIT = {
    TransactionStatus.AWAITING_APPROVAL,
    TransactionStatus.APPROVED,
    TransactionStatus.SUBMITTED,
    TransactionStatus.CONFIRMED,
}


def get_already_spent_today(
    db: Session, user_id: UUID, *, exclude_transaction_id: Optional[UUID] = None
) -> Decimal:
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    query = db.query(func.coalesce(func.sum(Transaction.amount_in), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.created_at >= start_of_day,
        Transaction.status.in_(_COUNTS_TOWARD_DAILY_LIMIT),
    )
    if exclude_transaction_id is not None:
        query = query.filter(Transaction.id != exclude_transaction_id)
    total = query.scalar()
    return Decimal(total or 0)


def evaluate_policy(
    *,
    policy: Policy,
    operation: str,
    amount: Decimal,
    protocol: str,
    action_type: Optional[str],
    risk_level: RiskLevel,
    already_spent_today: Decimal,
) -> PolicyDecision:
    """Pure function over its arguments -- no DB session, no I/O. Callers
    fetch `already_spent_today` themselves (get_already_spent_today, above)
    so this stays fast and trivially unit-testable."""
    checks: List[PolicyCheckResult] = []

    # 1. Max transaction amount
    if amount > policy.max_transaction_amount:
        checks.append(
            PolicyCheckResult(
                rule="max_transaction_amount",
                passed=False,
                detail=(
                    f"{amount} MON exceeds your max transaction amount of "
                    f"{policy.max_transaction_amount} MON."
                ),
            )
        )
    else:
        checks.append(
            PolicyCheckResult(
                rule="max_transaction_amount",
                passed=True,
                detail=f"{amount} MON is within your max transaction amount of {policy.max_transaction_amount} MON.",
            )
        )

    # 2. Daily limit
    projected_total = already_spent_today + amount
    if projected_total > policy.daily_limit:
        checks.append(
            PolicyCheckResult(
                rule="daily_limit",
                passed=False,
                detail=(
                    f"You've already committed {already_spent_today} MON today; adding {amount} MON "
                    f"would bring today's total to {projected_total} MON, over your daily limit of "
                    f"{policy.daily_limit} MON."
                ),
            )
        )
    else:
        checks.append(
            PolicyCheckResult(
                rule="daily_limit",
                passed=True,
                detail=f"Today's total would be {projected_total} MON, within your daily limit of {policy.daily_limit} MON.",
            )
        )

    # 3. Allowed protocols -- an empty list means "no restriction configured",
    # matching the Phase 1 default so a brand-new user isn't locked out of
    # every protocol before they've set anything up.
    if policy.allowed_protocols and protocol not in policy.allowed_protocols:
        checks.append(
            PolicyCheckResult(
                rule="allowed_protocols",
                passed=False,
                detail=f"Protocol '{protocol}' is not on your allowed-protocols list: {policy.allowed_protocols}.",
            )
        )
    else:
        checks.append(
            PolicyCheckResult(
                rule="allowed_protocols",
                passed=True,
                detail=(
                    f"Protocol '{protocol}' is permitted."
                    if policy.allowed_protocols
                    else "No protocol restriction configured."
                ),
            )
        )

    # 4. Allowed actions -- same empty-list convention as above.
    effective_action = (action_type or operation).upper()
    allowed_actions_upper = {a.upper() for a in policy.allowed_actions}
    if policy.allowed_actions and effective_action not in allowed_actions_upper:
        checks.append(
            PolicyCheckResult(
                rule="allowed_actions",
                passed=False,
                detail=f"Action '{effective_action}' is not on your allowed-actions list: {policy.allowed_actions}.",
            )
        )
    else:
        checks.append(
            PolicyCheckResult(
                rule="allowed_actions",
                passed=True,
                detail=(
                    f"Action '{effective_action}' is permitted."
                    if policy.allowed_actions
                    else "No action restriction configured."
                ),
            )
        )

    # 5. Max risk level
    if _RISK_RANK[risk_level] > _RISK_RANK[policy.max_risk_level]:
        checks.append(
            PolicyCheckResult(
                rule="max_risk_level",
                passed=False,
                detail=(
                    f"This action was scored {risk_level.value} risk, above your configured maximum of "
                    f"{policy.max_risk_level.value}."
                ),
            )
        )
    else:
        checks.append(
            PolicyCheckResult(
                rule="max_risk_level",
                passed=True,
                detail=(
                    f"This action was scored {risk_level.value} risk, within your configured maximum of "
                    f"{policy.max_risk_level.value}."
                ),
            )
        )

    failed = [c for c in checks if not c.passed]
    passed = len(failed) == 0

    return PolicyDecision(
        passed=passed,
        requires_approval=passed and policy.approval_required,
        checks=checks,
        reasons=[c.detail for c in failed],
    )


def determine_transaction_status(policy_decision: PolicyDecision) -> TransactionStatus:
    """The single place that turns a PolicyDecision into the Transaction
    status enum -- reused by both the AI flow and the standalone what-if
    endpoint so they can never disagree with each other.

    A failure on the `max_risk_level` rule specifically is reported as
    RISK_REJECTED ("too risky for what you allow"); any other failing
    rule (amount, daily limit, protocol/action not on the allow-list) is
    POLICY_REJECTED ("not permitted by your configured rules"). Both are
    deterministic outcomes of the same PolicyDecision -- this only picks
    which label best explains *why*.
    """
    if policy_decision.passed:
        return TransactionStatus.AWAITING_APPROVAL if policy_decision.requires_approval else TransactionStatus.APPROVED

    risk_rule_failed = any(c.rule == "max_risk_level" and not c.passed for c in policy_decision.checks)
    return TransactionStatus.RISK_REJECTED if risk_rule_failed else TransactionStatus.POLICY_REJECTED
