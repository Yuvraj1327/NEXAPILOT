"""
Structured output schema for the AI layer.

This is the contract Claude MUST fill in — enforced two ways: (1) it's
handed to the Anthropic API as a tool's input_schema, so the model is
steered toward this exact shape, and (2) whatever comes back is validated
against these same Pydantic models before anything else in the backend
ever sees it (see app/ai/service.py). AI output is untrusted input; this
is the deterministic gate it must pass, same as any other untrusted
input to the API.
"""

from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.enums import RiskLevel, TransactionStatus


class AIIntent(str, Enum):
    PORTFOLIO_ANALYSIS = "PORTFOLIO_ANALYSIS"
    OPPORTUNITY_DISCOVERY = "OPPORTUNITY_DISCOVERY"
    COMPARISON = "COMPARISON"
    TRANSACTION_PLAN = "TRANSACTION_PLAN"
    EXPLANATION = "EXPLANATION"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"


class OpportunityItem(BaseModel):
    """One yield/DeFi opportunity, as surfaced by the (demo/mock — see
    app/ai/opportunities.py) list_yield_opportunities tool."""

    protocol: str = Field(..., max_length=64)
    action_type: str = Field(..., max_length=32, description="e.g. STAKE, LEND, PROVIDE_LIQUIDITY")
    estimated_apy_percent: Optional[Decimal] = Field(default=None, ge=0, le=1000)
    risk_category: str = Field(..., description="LOW, MEDIUM, or HIGH")
    description: str = Field(..., max_length=500)

    @model_validator(mode="after")
    def _validate_risk_category(self) -> "OpportunityItem":
        if self.risk_category not in ("LOW", "MEDIUM", "HIGH"):
            raise ValueError("risk_category must be one of LOW, MEDIUM, HIGH")
        return self


class ProposedTransactionAction(BaseModel):
    """Claude's proposed on-chain action. This is a PROPOSAL only — it is
    never executed directly. It becomes a Transaction row in PENDING
    status, and must still pass the Risk Engine + Policy Engine (Phase 4)
    and explicit user approval (Phase 2's flow) before anything is ever
    signed or broadcast."""

    operation: str = Field(..., description="deposit, withdraw, or execute")
    amount: Decimal = Field(..., gt=0, description="Amount in whole MON, not wei.")
    protocol: str = Field(..., max_length=64)
    action_type: Optional[str] = Field(default=None, max_length=32)
    target_contract: Optional[str] = Field(default=None)
    reasoning: str = Field(..., max_length=1000, description="Why this action serves the user's request.")
    risk_notes: str = Field(..., max_length=1000, description="Claude's own risk callout — advisory only.")

    @model_validator(mode="after")
    def _validate_operation_shape(self) -> "ProposedTransactionAction":
        if self.operation not in ("deposit", "withdraw", "execute"):
            raise ValueError("operation must be one of: deposit, withdraw, execute")
        if self.operation == "execute" and not self.target_contract:
            raise ValueError("target_contract is required when operation is 'execute'")
        if self.operation == "execute" and not self.action_type:
            raise ValueError("action_type is required when operation is 'execute'")
        return self


class NexaPilotAIAction(BaseModel):
    """The single structured object every /ai/query call resolves to."""

    intent: AIIntent
    summary: str = Field(..., max_length=200, description="One-line headline of the response.")
    explanation: str = Field(..., max_length=3000, description="The full natural-language answer to the user.")
    opportunities: Optional[List[OpportunityItem]] = None
    proposed_transaction: Optional[ProposedTransactionAction] = None
    clarifying_question: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_payload_matches_intent(self) -> "NexaPilotAIAction":
        if self.intent == AIIntent.TRANSACTION_PLAN and self.proposed_transaction is None:
            raise ValueError("proposed_transaction is required when intent is TRANSACTION_PLAN")
        if self.intent == AIIntent.OPPORTUNITY_DISCOVERY and not self.opportunities:
            raise ValueError("opportunities (at least one) is required when intent is OPPORTUNITY_DISCOVERY")
        if self.intent == AIIntent.COMPARISON and (not self.opportunities or len(self.opportunities) < 2):
            raise ValueError("opportunities (at least two) is required when intent is COMPARISON")
        if self.intent == AIIntent.CLARIFICATION_NEEDED and not self.clarifying_question:
            raise ValueError("clarifying_question is required when intent is CLARIFICATION_NEEDED")
        return self


class AIQueryRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class AIQueryResponse(BaseModel):
    action: NexaPilotAIAction
    transaction_id: Optional[str] = Field(
        default=None, description="Set only for TRANSACTION_PLAN — a Transaction row was created."
    )
    tools_used: List[str] = Field(default_factory=list, description="Read-only data tools Claude actually called.")
    transaction_status: Optional[TransactionStatus] = Field(
        default=None,
        description=(
            "Set only for TRANSACTION_PLAN — the deterministic Risk Engine + Policy Engine verdict "
            "(RISK_REJECTED, POLICY_REJECTED, AWAITING_APPROVAL, or APPROVED). Never set by Claude."
        ),
    )
    risk_level: Optional[RiskLevel] = Field(
        default=None, description="Set only for TRANSACTION_PLAN — the Risk Engine's LOW/MEDIUM/HIGH verdict."
    )
