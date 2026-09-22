from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import RiskLevel


class RiskFactor(BaseModel):
    """One deterministic input into the risk score, kept individually
    visible so a LOW/MEDIUM/HIGH verdict is always explainable rather than
    a black box."""

    name: str
    detail: str
    raw_value: Optional[str] = None
    score: float = Field(..., ge=0, le=100, description="This factor's own 0-100 risk score.")
    weight_percent: float = Field(..., ge=0, le=100)
    contribution: float = Field(..., description="score * weight_percent / 100 -- this factor's share of the total.")


class RiskAssessment(BaseModel):
    risk_level: RiskLevel
    score: float = Field(..., ge=0, le=100)
    summary: str
    factors: List[RiskFactor]


class RiskAssessmentRequest(BaseModel):
    """Body for POST /api/v1/risk/assess -- the same shape as an AI
    ProposedTransactionAction, so a hypothetical action can be scored
    without going through Claude at all."""

    operation: str = Field(..., description="deposit, withdraw, or execute")
    amount: Decimal = Field(..., gt=0, description="Amount in whole MON, not wei.")
    protocol: str = Field(..., max_length=64)
    action_type: Optional[str] = Field(default=None, max_length=32)
