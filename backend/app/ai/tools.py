"""
Tool definitions Claude is given, and their backend-side dispatch.

Every tool here except `submit_nexapilot_action` is READ-ONLY — it looks
something up and returns it; none of them can create, sign, or send a
transaction, change a policy, or mutate anything. That's not a convention
Claude is asked to respect; it's a fact about what these Python functions
are physically capable of doing. `submit_nexapilot_action` isn't really a
"tool" in the sense of doing something — it's how we force Claude's final
answer into the exact JSON shape app/schemas/ai.py validates.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.ai.opportunities import list_demo_opportunities
from app.blockchain import service as blockchain_service
from app.blockchain.client import check_rpc_connection
from app.blockchain.deployment import get_executor_deployment
from app.core.exceptions import AppError
from app.models.policy import Policy
from app.models.user import User
from app.models.wallet import Wallet

logger = logging.getLogger("nexapilot.ai")


@dataclass
class ToolContext:
    """Everything a read-only tool call might need — scoped to the
    single authenticated user making the /ai/query request. There is no
    way for Claude to point a tool at someone else's wallet or data."""

    user: User
    wallet: Wallet
    policy: Policy
    db: Session


class UnknownToolError(AppError):
    status_code = 502
    code = "AI_UNKNOWN_TOOL_CALL"


def _decimal_str(value: Decimal) -> str:
    return format(value, "f")


def _get_wallet_balance(ctx: ToolContext, _input: Dict[str, Any]) -> Dict[str, Any]:
    native = blockchain_service.get_native_balance(ctx.wallet.address)
    vault = blockchain_service.get_vault_balance(ctx.wallet.address)
    return {
        "address": ctx.wallet.address,
        "chain": ctx.wallet.chain,
        "native_balance_mon": _decimal_str(native),
        "vault_balance_mon": _decimal_str(vault),
    }


def _get_user_policy(ctx: ToolContext, _input: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "max_transaction_amount_mon": _decimal_str(ctx.policy.max_transaction_amount),
        "daily_limit_mon": _decimal_str(ctx.policy.daily_limit),
        "allowed_protocols": ctx.policy.allowed_protocols,
        "allowed_actions": ctx.policy.allowed_actions,
        "max_risk_level": ctx.policy.max_risk_level.value,
        "approval_required": ctx.policy.approval_required,
        "note": (
            "These are the user's own configured limits. A proposed transaction still needs "
            "to clear the backend Risk Engine and Policy Engine, and the user's own approval, "
            "regardless of what you propose here."
        ),
    }


def _get_network_status(_ctx: ToolContext, _input: Dict[str, Any]) -> Dict[str, Any]:
    status = check_rpc_connection()
    try:
        status["contract_address"] = get_executor_deployment().address
    except AppError:
        status["contract_address"] = None
    return status


def _list_yield_opportunities(_ctx: ToolContext, _input: Dict[str, Any]) -> Dict[str, Any]:
    mock_address = None
    try:
        # Only meaningful on the local devnet fixture — see contracts/deployments.
        from app.core.config import settings

        deployments_file = settings.contracts_dir / "deployments" / f"{settings.blockchain_network}.json"
        if deployments_file.exists():
            import json

            data = json.loads(deployments_file.read_text())
            mock_address = data.get("auxiliaryFixtures", {}).get("mockProtocol", {}).get("address")
    except Exception as exc:  # noqa: BLE001 — this is best-effort enrichment, never fatal
        logger.warning("Could not resolve mock protocol fixture address: %s", exc)

    return {
        "disclaimer": "DEMO data for this hackathon build — not live market data from real protocols.",
        "opportunities": list_demo_opportunities(mock_address),
    }


_READ_ONLY_DISPATCH = {
    "get_wallet_balance": _get_wallet_balance,
    "get_user_policy": _get_user_policy,
    "get_network_status": _get_network_status,
    "list_yield_opportunities": _list_yield_opportunities,
}


def dispatch_read_only_tool(name: str, tool_input: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    handler = _READ_ONLY_DISPATCH.get(name)
    if handler is None:
        raise UnknownToolError(f"Claude called an unknown tool: '{name}'.")
    return handler(ctx, tool_input)


READ_ONLY_TOOL_DEFINITIONS = [
    {
        "name": "get_wallet_balance",
        "description": (
            "Get the current user's own connected wallet balance: native MON held in the "
            "wallet, and MON tracked for them inside the NexaPilotExecutor vault contract."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_user_policy",
        "description": (
            "Get the current user's own configured spending policy: max transaction amount, "
            "daily limit, allowed protocols/actions, max risk level, and approval requirement."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_network_status",
        "description": "Check whether the Monad RPC connection is up and get the latest block number.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_yield_opportunities",
        "description": (
            "List demo DeFi yield opportunities (protocol, action type, illustrative APY, risk "
            "category, description) available for this hackathon build. NOT live market data."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]

# Hand-written to exactly match app/schemas/ai.NexaPilotAIAction — kept in
# sync manually rather than auto-derived from the Pydantic model, since
# Anthropic's tool JSON-schema subset and Pydantic's auto-generated schema
# (Decimal/Enum rendering, $defs, etc.) don't line up cleanly, and a
# hand-written schema is easier to reason about for what we're steering
# the model toward. Backend validation always re-checks this against the
# real Pydantic model regardless — this schema is a steering aid, not the
# source of truth for what's accepted.
SUBMIT_ACTION_TOOL_DEFINITION = {
    "name": "submit_nexapilot_action",
    "description": "Submit your final, structured response. This must be the last tool you call.",
    "input_schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "PORTFOLIO_ANALYSIS",
                    "OPPORTUNITY_DISCOVERY",
                    "COMPARISON",
                    "TRANSACTION_PLAN",
                    "EXPLANATION",
                    "CLARIFICATION_NEEDED",
                ],
            },
            "summary": {"type": "string", "maxLength": 200, "description": "One-line headline."},
            "explanation": {"type": "string", "maxLength": 3000, "description": "The full answer to the user."},
            "opportunities": {
                "type": "array",
                "description": "Required for OPPORTUNITY_DISCOVERY (>=1) and COMPARISON (>=2).",
                "items": {
                    "type": "object",
                    "properties": {
                        "protocol": {"type": "string"},
                        "action_type": {"type": "string"},
                        "estimated_apy_percent": {"type": "number"},
                        "risk_category": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                        "description": {"type": "string"},
                    },
                    "required": ["protocol", "action_type", "risk_category", "description"],
                },
            },
            "proposed_transaction": {
                "type": "object",
                "description": "Required for TRANSACTION_PLAN. A proposal only — never executed by you.",
                "properties": {
                    "operation": {"type": "string", "enum": ["deposit", "withdraw", "execute"]},
                    "amount": {"type": "number", "exclusiveMinimum": 0, "description": "Whole MON, not wei."},
                    "protocol": {"type": "string"},
                    "action_type": {"type": "string"},
                    "target_contract": {"type": "string", "description": "Required if operation is 'execute'."},
                    "reasoning": {"type": "string"},
                    "risk_notes": {"type": "string"},
                },
                "required": ["operation", "amount", "protocol", "reasoning", "risk_notes"],
            },
            "clarifying_question": {
                "type": "string",
                "description": "Required for CLARIFICATION_NEEDED — exactly one clear question.",
            },
        },
        "required": ["intent", "summary", "explanation"],
    },
}
