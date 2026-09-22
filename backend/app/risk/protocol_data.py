"""
Deterministic protocol risk registry (Phase 4).

Liquidity and volatility scores are derived from a protocol's demo
`risk_category` rather than hand-tuned per protocol, because NexaPilot has
no live external market-data feed in this MVP (see app/ai/opportunities.py)
and fabricating protocol-specific precision we have no data source for
would be dishonest. The category -> score mapping is itself the
deterministic, documented rule.

The protocol list is built FROM `app.ai.opportunities.DEMO_OPPORTUNITIES`
— the same demo dataset Claude is given as a read-only tool result — so
the Risk Engine's view of a protocol's risk category can never drift out
of sync with what Claude tells the user about it. `nexapilot-vault` isn't
a yield "opportunity" (it's NexaPilot's own minimal, audited executor
contract that plain deposit/withdraw operations target), so it's added
here explicitly as the lowest-risk baseline.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Optional

from app.ai.opportunities import DEMO_OPPORTUNITIES
from app.models.enums import RiskLevel


@dataclass(frozen=True)
class ProtocolProfile:
    protocol: str
    category: RiskLevel
    liquidity_score: float  # 0 (illiquid) - 100 (highly liquid)
    volatility_score: float  # 0 (stable) - 100 (highly volatile)
    estimated_apy_percent: Optional[Decimal]
    known: bool = True


# category -> (liquidity_score, volatility_score). Higher liquidity is
# lower risk; higher volatility is higher risk.
_CATEGORY_LIQUIDITY_VOLATILITY = {
    RiskLevel.LOW: (80.0, 15.0),
    RiskLevel.MEDIUM: (50.0, 45.0),
    RiskLevel.HIGH: (25.0, 75.0),
}

# A protocol NexaPilot has never heard of gets the most cautious deterministic
# defaults available -- "unknown" is treated as strictly riskier than even
# the HIGH demo category, since there's no data backing it at all.
UNKNOWN_LIQUIDITY_VOLATILITY = (15.0, 85.0)


def _build_registry() -> Dict[str, ProtocolProfile]:
    registry: Dict[str, ProtocolProfile] = {
        "nexapilot-vault": ProtocolProfile(
            protocol="nexapilot-vault",
            category=RiskLevel.LOW,
            liquidity_score=95.0,  # instant deposit/withdraw, no external dependency
            volatility_score=5.0,
            estimated_apy_percent=Decimal("0"),
        )
    }
    for item in DEMO_OPPORTUNITIES:
        category = RiskLevel(item["risk_category"])
        liquidity, volatility = _CATEGORY_LIQUIDITY_VOLATILITY[category]
        apy = item.get("estimated_apy_percent")
        registry[item["protocol"]] = ProtocolProfile(
            protocol=item["protocol"],
            category=category,
            liquidity_score=liquidity,
            volatility_score=volatility,
            estimated_apy_percent=Decimal(str(apy)) if apy is not None else None,
        )
    return registry


PROTOCOL_REGISTRY: Dict[str, ProtocolProfile] = _build_registry()


def get_protocol_profile(protocol: str) -> ProtocolProfile:
    """Never raises -- an unrecognized protocol name gets a conservative
    "unknown" profile rather than blocking the risk assessment itself.
    Whether an unknown/unrecognized protocol is *allowed at all* is the
    Policy Engine's job (allowed_protocols), not this lookup's."""
    profile = PROTOCOL_REGISTRY.get(protocol)
    if profile is not None:
        return profile
    liquidity, volatility = UNKNOWN_LIQUIDITY_VOLATILITY
    return ProtocolProfile(
        protocol=protocol,
        category=RiskLevel.HIGH,
        liquidity_score=liquidity,
        volatility_score=volatility,
        estimated_apy_percent=None,
        known=False,
    )
