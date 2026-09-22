"""
AI layer tests using a scripted fake Anthropic client — no real API calls,
no network, no cost, fully deterministic. This is the recommended path
from the Phase 3 kickoff: prove the tool-use loop, the Pydantic validation
gate, the self-correction retry, and the "AI can't execute anything" and
"transaction plans land as PENDING, not live" properties without needing a
real ANTHROPIC_API_KEY. Point a real key at backend/.env and everything
here still runs unchanged against the live API.
"""

from typing import List

import pytest
from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

from app.ai import service as ai_service_module
from app.ai.tools import READ_ONLY_TOOL_DEFINITIONS, ToolContext, dispatch_read_only_tool
from app.ai.tools import UnknownToolError
from app.core.exceptions import AppError
from app.models.policy import Policy
from app.models.user import User
from app.models.wallet import Wallet


def _message(content, stop_reason="tool_use") -> Message:
    return Message(
        id="msg_test",
        type="message",
        role="assistant",
        model="claude-sonnet-5",
        content=content,
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=10),
    )


def tool_use(name: str, input: dict, tool_id: str = "tu_1") -> ToolUseBlock:
    return ToolUseBlock(type="tool_use", id=tool_id, name=name, input=input)


class ScriptedAnthropicMessages:
    """Stands in for client.messages — replays a fixed list of Message
    responses, one per .create() call, in order."""

    def __init__(self, script: List[Message]):
        self._script = list(script)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._script:
            raise AssertionError("ScriptedAnthropicMessages ran out of scripted responses.")
        return self._script.pop(0)


class ScriptedAnthropicClient:
    def __init__(self, script: List[Message]):
        self.messages = ScriptedAnthropicMessages(script)


def _connect_and_get_context(client, db_session, address: str) -> ToolContext:
    resp = client.post("/api/v1/auth/connect", json={"address": address, "chain": "monad"})
    assert resp.status_code == 200
    auth = resp.json()
    user = db_session.get(User, auth["user"]["id"])
    wallet = db_session.get(Wallet, auth["wallet"]["id"])
    policy = db_session.query(Policy).filter(Policy.user_id == user.id).first()
    return ToolContext(user=user, wallet=wallet, policy=policy, db=db_session), auth


# --- direct service-level tests (no HTTP, fastest signal) ---


def test_single_turn_explanation(monkeypatch, client, db_session):
    ctx, _ = _connect_and_get_context(client, db_session, "0xaaaa000000000000000000000000000000000000")

    script = [
        _message(
            [
                tool_use(
                    "submit_nexapilot_action",
                    {
                        "intent": "EXPLANATION",
                        "summary": "What is APY?",
                        "explanation": "APY is the annual percentage yield, including compounding.",
                    },
                )
            ]
        )
    ]
    fake_client = ScriptedAnthropicClient(script)
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client)

    action, tools_used = ai_service_module.run_ai_query(ctx=ctx, message="What is APY?")

    assert action.intent.value == "EXPLANATION"
    assert tools_used == []
    assert len(fake_client.messages.calls) == 1


def test_reads_wallet_balance_before_answering(monkeypatch, client, db_session):
    ctx, _ = _connect_and_get_context(client, db_session, "0xbbbb000000000000000000000000000000000000")

    script = [
        _message([tool_use("get_wallet_balance", {}, tool_id="tu_bal")]),
        _message(
            [
                tool_use(
                    "submit_nexapilot_action",
                    {
                        "intent": "PORTFOLIO_ANALYSIS",
                        "summary": "Your portfolio",
                        "explanation": "You currently hold 0 MON in your wallet and 0 MON in the vault.",
                    },
                    tool_id="tu_final",
                )
            ]
        ),
    ]
    fake_client = ScriptedAnthropicClient(script)
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client)

    action, tools_used = ai_service_module.run_ai_query(ctx=ctx, message="How's my portfolio?")

    assert action.intent.value == "PORTFOLIO_ANALYSIS"
    assert tools_used == ["get_wallet_balance"]
    # second call must include the tool_result from the first
    def _block_type(block):
        # Blocks are either plain dicts (our own tool_result messages) or
        # Anthropic SDK Pydantic objects (assistant content echoed back
        # verbatim) -- read "type" whichever shape it is.
        if isinstance(block, dict):
            return block.get("type")
        return getattr(block, "type", None)

    second_call_messages = fake_client.messages.calls[1]["messages"]
    assert any(
        isinstance(m.get("content"), list)
        and any(_block_type(block) == "tool_result" for block in m["content"])
        for m in second_call_messages
        if isinstance(m, dict)
    )


def test_invalid_output_triggers_self_correction_then_succeeds(monkeypatch, client, db_session):
    ctx, _ = _connect_and_get_context(client, db_session, "0xcccc000000000000000000000000000000000000")

    # First attempt: TRANSACTION_PLAN without the required proposed_transaction -> invalid.
    bad = _message(
        [tool_use("submit_nexapilot_action", {"intent": "TRANSACTION_PLAN", "summary": "x", "explanation": "y"}, tool_id="tu_bad")]
    )
    # Second attempt: corrected, valid payload.
    good = _message(
        [
            tool_use(
                "submit_nexapilot_action",
                {
                    "intent": "TRANSACTION_PLAN",
                    "summary": "Stake 5 MON",
                    "explanation": "Proposing a demo stake of 5 MON.",
                    "proposed_transaction": {
                        "operation": "deposit",
                        "amount": 5,
                        "protocol": "nexapilot-vault",
                        "reasoning": "User asked to deposit.",
                        "risk_notes": "Low risk, standard vault deposit.",
                    },
                },
                tool_id="tu_good",
            )
        ]
    )
    fake_client = ScriptedAnthropicClient([bad, good])
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client)

    action, tools_used = ai_service_module.run_ai_query(ctx=ctx, message="Deposit 5 MON")

    assert action.intent.value == "TRANSACTION_PLAN"
    assert action.proposed_transaction.amount == 5
    assert len(fake_client.messages.calls) == 2


def test_output_validation_exhausts_retries_and_raises(monkeypatch, client, db_session):
    ctx, _ = _connect_and_get_context(client, db_session, "0xdddd000000000000000000000000000000000000")

    always_bad = lambda i: _message(
        [tool_use("submit_nexapilot_action", {"intent": "TRANSACTION_PLAN", "summary": "x", "explanation": "y"}, tool_id=f"tu_{i}")]
    )
    from app.core.config import settings

    script = [always_bad(i) for i in range(settings.ai_max_output_retries + 2)]
    fake_client = ScriptedAnthropicClient(script)
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client)

    with pytest.raises(AppError) as exc_info:
        ai_service_module.run_ai_query(ctx=ctx, message="Deposit 5 MON")
    assert exc_info.value.code == "AI_OUTPUT_INVALID"


def test_no_tool_call_at_all_raises_service_error(monkeypatch, client, db_session):
    ctx, _ = _connect_and_get_context(client, db_session, "0xeeee000000000000000000000000000000000000")

    script = [_message([TextBlock(type="text", text="I'll just answer in prose.")], stop_reason="end_turn")]
    fake_client = ScriptedAnthropicClient(script)
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client)

    with pytest.raises(AppError) as exc_info:
        ai_service_module.run_ai_query(ctx=ctx, message="hi")
    assert exc_info.value.code == "AI_SERVICE_ERROR"


# --- HTTP-level test: full endpoint, including Phase 4 Risk/Policy wiring ---


def test_transaction_plan_endpoint_runs_risk_and_policy_checks(monkeypatch, client, db_session):
    resp = client.post(
        "/api/v1/auth/connect", json={"address": "0xffff000000000000000000000000000000000000", "chain": "monad"}
    )
    auth = resp.json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    good = _message(
        [
            tool_use(
                "submit_nexapilot_action",
                {
                    "intent": "TRANSACTION_PLAN",
                    "summary": "Deposit 10 MON",
                    "explanation": "Depositing 10 MON into your NexaPilot vault as requested.",
                    "proposed_transaction": {
                        "operation": "deposit",
                        "amount": 10,
                        "protocol": "nexapilot-vault",
                        "reasoning": "User asked to deposit 10 MON.",
                        "risk_notes": "Standard vault deposit, low risk.",
                    },
                },
            )
        ]
    )
    fake_client = ScriptedAnthropicClient([good])
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client)

    resp = client.post("/api/v1/ai/query", headers=headers, json={"message": "Deposit 10 MON for me"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"]["intent"] == "TRANSACTION_PLAN"
    assert body["transaction_id"] is not None
    # A small deposit into NexaPilot's own audited vault, well within the
    # default policy's limits, should clear both engines and land on
    # AWAITING_APPROVAL (the default policy requires explicit approval).
    assert body["risk_level"] == "LOW"
    assert body["transaction_status"] == "AWAITING_APPROVAL"

    tx_resp = client.get(f"/api/v1/transactions/{body['transaction_id']}", headers=headers)
    assert tx_resp.status_code == 200
    tx = tx_resp.json()
    assert tx["status"] == "AWAITING_APPROVAL"  # passed Risk Check + Policy Check
    assert tx["risk_level"] == "LOW"
    assert tx["risk_explanation"] is not None
    assert tx["policy_decision"]["passed"] is True
    assert float(tx["amount_in"]) == 10  # Numeric(30,10) serializes with full decimal precision
    assert tx["protocol"] == "nexapilot-vault"

    activity_resp = client.get("/api/v1/activity", headers=headers)
    assert activity_resp.status_code == 200
    assert any(a["type"] == "RECOMMENDATION" for a in activity_resp.json())


def test_informational_intent_does_not_create_a_transaction(monkeypatch, client, db_session):
    resp = client.post(
        "/api/v1/auth/connect", json={"address": "0x1111222233334444555566667777888899990000", "chain": "monad"}
    )
    auth = resp.json()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    good = _message(
        [
            tool_use(
                "submit_nexapilot_action",
                {"intent": "EXPLANATION", "summary": "What is liquidity?", "explanation": "Liquidity means..."},
            )
        ]
    )
    fake_client = ScriptedAnthropicClient([good])
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client)

    resp = client.post("/api/v1/ai/query", headers=headers, json={"message": "What is liquidity?"})
    assert resp.status_code == 200
    assert resp.json()["transaction_id"] is None

    tx_list = client.get("/api/v1/transactions", headers=headers)
    assert tx_list.json() == []


# --- safety property: no execution capability exists to dispatch to ---


def test_only_read_only_tools_are_dispatchable(client, db_session):
    ctx, _ = _connect_and_get_context(client, db_session, "0x2222333344445555666677778888999900001111")

    names = {t["name"] for t in READ_ONLY_TOOL_DEFINITIONS}
    assert names == {"get_wallet_balance", "get_user_policy", "get_network_status", "list_yield_opportunities"}
    for forbidden in ("execute", "send_transaction", "sign", "submit_nexapilot_action", "withdraw", "transfer"):
        assert forbidden not in names

    with pytest.raises(UnknownToolError):
        dispatch_read_only_tool("execute_transaction", {}, ctx)
