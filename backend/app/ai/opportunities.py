"""
DEMO/MOCK yield-opportunity data.

NexaPilot has no live integration with real external Monad DeFi protocols
yet (that's real future work, well beyond this hackathon MVP). Rather than
have Claude invent plausible-sounding protocols and APYs on the fly — which
would be presented to a user as fact — this is a small, explicit, clearly
fictional dataset the AI service hands Claude as tool output. The system
prompt (app/ai/prompts.py) tells Claude these are illustrative demo
opportunities, not live external data, and Claude is expected to say so to
the user too.

Swap this module for a real data source (DefiLlama, direct protocol
indexing, etc.) without touching the AI service or its schemas — the tool
contract (list of OpportunityItem-shaped dicts) stays the same.
"""

from typing import Any, Dict, List

# All addresses below are illustrative placeholders, NOT real deployed
# contracts, except MOCK_PROTOCOL_ADDRESS which is filled in at runtime
# from contracts/deployments/<network>.json's test fixture so the demo
# "STAKE" opportunity is something a follow-up TRANSACTION_PLAN can
# actually target on the local devnet.
DEMO_OPPORTUNITIES: List[Dict[str, Any]] = [
    {
        "protocol": "NexaStake",
        "action_type": "STAKE",
        "estimated_apy_percent": "4.2",
        "risk_category": "LOW",
        "description": (
            "Demo staking pool with a small, well-tested contract and no leverage. "
            "Illustrative APY for this hackathon demo, not a live market rate."
        ),
        "uses_mock_protocol_fixture": True,
    },
    {
        "protocol": "TidalLend",
        "action_type": "LEND",
        "estimated_apy_percent": "7.8",
        "risk_category": "MEDIUM",
        "description": (
            "Demo lending market — higher illustrative yield reflects lending/liquidation "
            "risk in a real protocol of this kind. Not a live market rate."
        ),
        "uses_mock_protocol_fixture": False,
    },
    {
        "protocol": "MonadLoop",
        "action_type": "PROVIDE_LIQUIDITY",
        "estimated_apy_percent": "15.5",
        "risk_category": "HIGH",
        "description": (
            "Demo leveraged liquidity-looping strategy — illustrative high yield paired with "
            "illustrative high risk (impermanent loss + leverage). Not a live market rate."
        ),
        "uses_mock_protocol_fixture": False,
    },
]


def list_demo_opportunities(mock_protocol_address: str | None) -> List[Dict[str, Any]]:
    """Return the demo dataset, filling in a real, allow-listed on-chain
    target address for the one opportunity that's actually wired up to the
    local devnet's MockProtocol fixture (so a TRANSACTION_PLAN referencing
    it can actually be prepared in Phase 2's flow)."""
    results = []
    for item in DEMO_OPPORTUNITIES:
        entry = {k: v for k, v in item.items() if k != "uses_mock_protocol_fixture"}
        if item["uses_mock_protocol_fixture"] and mock_protocol_address:
            entry["target_contract"] = mock_protocol_address
        results.append(entry)
    return results
