"""
Deterministic Risk Engine (Phase 4).

Scores a proposed on-chain action into an explainable LOW / MEDIUM / HIGH
risk level from fixed, rule-based factors -- protocol risk category,
liquidity, volatility, illustrative APY, transaction-amount concentration,
and operation type. Same inputs always produce the same output, and every
factor's contribution is returned so a rejection can always be explained.

This is emphatically NOT an AI judgment call. Claude's own `risk_notes`
field (see app/schemas/ai.py's ProposedTransactionAction) is advisory-only
free text Claude writes for the user's benefit; it is never read by this
module and carries no weight in the score. "AI recommendations are never
trusted directly" (project rule) applies here in the most literal sense:
this file doesn't import anything from app.ai except the static demo
protocol data both this and Claude read from.
"""

from decimal import Decimal
from typing import List, Optional

from app.models.enums import RiskLevel
from app.risk.protocol_data import get_protocol_profile
from app.schemas.risk import RiskAssessment, RiskFactor

# --- factor weights (must sum to 100) ---
_WEIGHT_PROTOCOL_CATEGORY = 25.0
_WEIGHT_LIQUIDITY = 15.0
_WEIGHT_VOLATILITY = 15.0
_WEIGHT_APY = 15.0
_WEIGHT_AMOUNT = 20.0
_WEIGHT_OPERATION = 10.0

assert (
    _WEIGHT_PROTOCOL_CATEGORY
    + _WEIGHT_LIQUIDITY
    + _WEIGHT_VOLATILITY
    + _WEIGHT_APY
    + _WEIGHT_AMOUNT
    + _WEIGHT_OPERATION
    == 100.0
)

_CATEGORY_SCORE = {RiskLevel.LOW: 15.0, RiskLevel.MEDIUM: 50.0, RiskLevel.HIGH: 90.0}
_UNKNOWN_CATEGORY_SCORE = 100.0

_OPERATION_SCORE = {
    "deposit": 10.0,  # into NexaPilot's own audited vault
    "withdraw": 25.0,  # still vault-only, but reduces custody safeguards
    "execute": 70.0,  # an arbitrary external contract call
}
_UNKNOWN_OPERATION_SCORE = 100.0

# amount thresholds, in whole MON -- used when no live wallet balance is
# available to compute a concentration ratio instead (see _amount_factor).
_ABSOLUTE_AMOUNT_BUCKETS = [
    (Decimal("1"), 10.0),
    (Decimal("10"), 30.0),
    (Decimal("50"), 55.0),
    (Decimal("200"), 80.0),
]
_ABSOLUTE_AMOUNT_OVERFLOW_SCORE = 100.0

_CONCENTRATION_BUCKETS = [
    (Decimal("0.15"), 15.0),
    (Decimal("0.40"), 40.0),
    (Decimal("0.75"), 70.0),
]
_CONCENTRATION_OVERFLOW_SCORE = 100.0

_APY_BUCKETS = [
    (Decimal("5"), 10.0),
    (Decimal("10"), 35.0),
    (Decimal("20"), 65.0),
]
_APY_OVERFLOW_SCORE = 95.0
_APY_UNKNOWN_SCORE = 50.0  # neutral -- no APY data either way

_LOW_MEDIUM_BOUNDARY = 35.0
_MEDIUM_HIGH_BOUNDARY = 70.0


def _bucket_score(value: Decimal, buckets: List[tuple], overflow_score: float) -> float:
    for threshold, score in buckets:
        if value <= threshold:
            return score
    return overflow_score


def _amount_factor(amount: Decimal, wallet_balance: Optional[Decimal]) -> RiskFactor:
    if wallet_balance is not None and wallet_balance > 0:
        ratio = amount / wallet_balance
        score = _bucket_score(ratio, _CONCENTRATION_BUCKETS, _CONCENTRATION_OVERFLOW_SCORE)
        detail = (
            f"{amount} MON is {ratio * 100:.1f}% of the wallet's current {wallet_balance} MON balance."
        )
        raw_value = f"{ratio:.4f}"
    elif wallet_balance is not None and wallet_balance == 0:
        score = _CONCENTRATION_OVERFLOW_SCORE
        detail = f"Wallet balance is 0 MON, so {amount} MON is more than the entire wallet."
        raw_value = "inf"
    else:
        score = _bucket_score(amount, _ABSOLUTE_AMOUNT_BUCKETS, _ABSOLUTE_AMOUNT_OVERFLOW_SCORE)
        detail = f"{amount} MON assessed on an absolute scale (wallet balance unavailable)."
        raw_value = str(amount)
    return RiskFactor(
        name="amount_concentration",
        detail=detail,
        raw_value=raw_value,
        score=score,
        weight_percent=_WEIGHT_AMOUNT,
        contribution=score * _WEIGHT_AMOUNT / 100,
    )


def _apy_factor(apy: Optional[Decimal]) -> RiskFactor:
    if apy is None:
        return RiskFactor(
            name="estimated_apy",
            detail="No APY data available for this protocol.",
            raw_value=None,
            score=_APY_UNKNOWN_SCORE,
            weight_percent=_WEIGHT_APY,
            contribution=_APY_UNKNOWN_SCORE * _WEIGHT_APY / 100,
        )
    score = _bucket_score(apy, _APY_BUCKETS, _APY_OVERFLOW_SCORE)
    return RiskFactor(
        name="estimated_apy",
        detail=f"Illustrative APY of {apy}% -- unusually high yield is itself a risk signal.",
        raw_value=str(apy),
        score=score,
        weight_percent=_WEIGHT_APY,
        contribution=score * _WEIGHT_APY / 100,
    )


def assess_risk(
    *,
    operation: str,
    amount: Decimal,
    protocol: str,
    action_type: Optional[str] = None,
    wallet_balance: Optional[Decimal] = None,
) -> RiskAssessment:
    """Pure function: same inputs -> same RiskAssessment, always. No I/O,
    no RPC calls, no AI -- `wallet_balance` is an optional caller-supplied
    input (the caller may fetch it from the blockchain layer, best-effort)
    rather than something this function reaches out to get itself, so this
    stays a fast, deterministic, unit-testable function."""
    profile = get_protocol_profile(protocol)

    category_score = _CATEGORY_SCORE.get(profile.category, _UNKNOWN_CATEGORY_SCORE) if profile.known else _UNKNOWN_CATEGORY_SCORE
    protocol_factor = RiskFactor(
        name="protocol_risk_category",
        detail=(
            f"'{protocol}' is a known protocol rated {profile.category.value}."
            if profile.known
            else f"'{protocol}' is not a recognized protocol -- treated as maximum caution."
        ),
        raw_value=profile.category.value if profile.known else "UNKNOWN",
        score=category_score,
        weight_percent=_WEIGHT_PROTOCOL_CATEGORY,
        contribution=category_score * _WEIGHT_PROTOCOL_CATEGORY / 100,
    )

    liquidity_score = 100.0 - profile.liquidity_score
    liquidity_factor = RiskFactor(
        name="liquidity",
        detail=f"Liquidity score {profile.liquidity_score:.0f}/100 (higher is more liquid, lower risk).",
        raw_value=f"{profile.liquidity_score:.0f}",
        score=liquidity_score,
        weight_percent=_WEIGHT_LIQUIDITY,
        contribution=liquidity_score * _WEIGHT_LIQUIDITY / 100,
    )

    volatility_factor = RiskFactor(
        name="volatility",
        detail=f"Volatility score {profile.volatility_score:.0f}/100 (higher is more volatile, more risk).",
        raw_value=f"{profile.volatility_score:.0f}",
        score=profile.volatility_score,
        weight_percent=_WEIGHT_VOLATILITY,
        contribution=profile.volatility_score * _WEIGHT_VOLATILITY / 100,
    )

    apy_factor = _apy_factor(profile.estimated_apy_percent)
    amount_factor = _amount_factor(amount, wallet_balance)

    op_key = (operation or "").lower()
    operation_score = _OPERATION_SCORE.get(op_key, _UNKNOWN_OPERATION_SCORE)
    operation_detail = (
        f"Operation '{operation}' targets NexaPilot's own audited vault contract."
        if op_key in ("deposit", "withdraw")
        else f"Operation '{operation}' calls out to an external contract ({action_type or 'unspecified action'})."
        if op_key == "execute"
        else f"Unrecognized operation '{operation}'."
    )
    operation_factor = RiskFactor(
        name="operation_type",
        detail=operation_detail,
        raw_value=operation,
        score=operation_score,
        weight_percent=_WEIGHT_OPERATION,
        contribution=operation_score * _WEIGHT_OPERATION / 100,
    )

    factors = [protocol_factor, liquidity_factor, volatility_factor, apy_factor, amount_factor, operation_factor]
    total_score = round(sum(f.contribution for f in factors), 2)

    if total_score < _LOW_MEDIUM_BOUNDARY:
        risk_level = RiskLevel.LOW
    elif total_score < _MEDIUM_HIGH_BOUNDARY:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.HIGH

    summary = (
        f"{risk_level.value} risk (score {total_score:.1f}/100) for a {operation} of {amount} MON "
        f"via '{protocol}'."
    )

    return RiskAssessment(risk_level=risk_level, score=total_score, summary=summary, factors=factors)
