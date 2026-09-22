from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import RiskLevel, TransactionStatus
from app.schemas.common import IDTimestampMixin, ORMBase


class PolicyRead(ORMBase, IDTimestampMixin):
    max_transaction_amount: Decimal
    daily_limit: Decimal
    allowed_protocols: List[str]
    allowed_actions: List[str]
    max_risk_level: RiskLevel
    approval_required: bool


class PolicyUpdate(BaseModel):
    """Phase 1 exposes policy as user-editable settings.

    Evaluating a proposed transaction against these values is the Policy
    Engine's job (Phase 4), not this schema's.
    """

    max_transaction_amount: Decimal = Field(gt=0)
    daily_limit: Decimal = Field(gt=0)
    allowed_protocols: List[str] = Field(default_factory=list)
    allowed_actions: List[str] = Field(default_factory=list)
    max_risk_level: RiskLevel = RiskLevel.MEDIUM
    approval_required: bool = True


# --- Policy Engine (Phase 4) ---


class PolicyCheckResult(BaseModel):
    """One independent, deterministic rule evaluation. Every check runs
    regardless of whether an earlier one already failed, so a rejection
    always lists every reason at once rather than stopping at the first."""

    rule: str
    passed: bool
    detail: str


class PolicyEvaluationRequest(BaseModel):
    """Body for POST /api/v1/policy/evaluate -- the same shape as an AI
    ProposedTransactionAction, so a hypothetical action can be run through
    Risk Check -> Policy Check without going through Claude at all."""

    operation: str = Field(..., description="deposit, withdraw, or execute")
    amount: Decimal = Field(..., gt=0, description="Amount in whole MON, not wei.")
    protocol: str = Field(..., max_length=64)
    action_type: Optional[str] = Field(default=None, max_length=32)


class PolicyDecision(BaseModel):
    passed: bool
    requires_approval: bool = Field(
        ..., description="True if it passed and the user's policy requires explicit approval before execution."
    )
    checks: List[PolicyCheckResult]
    reasons: List[str] = Field(default_factory=list, description="detail of every failed check, if any.")


class PolicyEvaluationResponse(BaseModel):
    """The full Phase 4 pipeline result for a hypothetical action: Risk
    Check -> Policy Check -> final PASS/REJECT status, exactly mirroring
    what a real Claude-generated TRANSACTION_PLAN goes through."""

    risk_level: RiskLevel
    risk_score: float
    policy_decision: PolicyDecision
    final_status: TransactionStatus


class PolicyUsage(BaseModel):
    """How much of the user's daily limit has already been committed
    today, for a frontend to show remaining headroom."""

    daily_limit: Decimal
    spent_today: Decimal
    remaining_today: Decimal
