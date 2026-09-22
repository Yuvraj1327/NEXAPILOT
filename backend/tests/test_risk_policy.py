"""
Phase 4 tests: deterministic Risk Engine + Policy Engine.

Three layers, matching the phase's own required test ("Claude action ->
Risk Check -> Policy Check -> PASS/REJECT"):

1. Pure unit tests of app.risk.engine.assess_risk and
   app.policy_engine.engine.evaluate_policy / determine_transaction_status
   -- no DB, no HTTP, fastest signal, and proof these functions are
   genuinely deterministic (same inputs -> same outputs every time).
2. HTTP-level tests of the standalone /api/v1/risk and /api/v1/policy
   endpoints.
3. Full end-to-end tests through /api/v1/ai/query using the same scripted
   fake Anthropic client as tests/test_ai.py, proving a Claude-generated
   TRANSACTION_PLAN actually gets rejected (or approved) by these
   deterministic engines and not by anything Claude said.
"""

from decimal import Decimal

from app.models.enums import RiskLevel, TransactionStatus
from app.models.policy import Policy
from app.policy_engine.engine import determine_transaction_status, evaluate_policy
from app.risk.engine import assess_risk
from app.schemas.policy import PolicyCheckResult, PolicyDecision
from tests.test_ai import ScriptedAnthropicClient, _message, tool_use
from tests.test_ai import ai_service_module

# ---------------------------------------------------------------------
# 1. Risk Engine -- pure unit tests
# ---------------------------------------------------------------------


def test_small_deposit_to_vault_is_low_risk():
    result = assess_risk(operation="deposit", amount=Decimal("5"), protocol="nexapilot-vault")
    assert result.risk_level == RiskLevel.LOW
    assert len(result.factors) == 6


def test_execute_to_unknown_protocol_large_amount_is_high_risk():
    result = assess_risk(
        operation="execute",
        amount=Decimal("500"),
        protocol="TotallyUnheardOfProtocol",
        action_type="FARM",
    )
    assert result.risk_level == RiskLevel.HIGH
    protocol_factor = next(f for f in result.factors if f.name == "protocol_risk_category")
    assert protocol_factor.raw_value == "UNKNOWN"


def test_known_medium_protocol_moderate_amount_is_medium_risk():
    # TidalLend is the demo MEDIUM-risk_category opportunity (see
    # app/ai/opportunities.py) -- assert against the engine's own output
    # rather than hardcoding a duplicate expectation of its APY/category.
    result = assess_risk(operation="execute", amount=Decimal("20"), protocol="TidalLend", action_type="LEND")
    assert result.risk_level == RiskLevel.MEDIUM


def test_same_amount_is_riskier_against_a_smaller_wallet_balance():
    # Concentration risk: 10 MON out of a 1000 MON wallet is trivial; 10
    # MON out of an 11 MON wallet is nearly everything the wallet holds.
    small_wallet = assess_risk(
        operation="deposit", amount=Decimal("10"), protocol="nexapilot-vault", wallet_balance=Decimal("11")
    )
    large_wallet = assess_risk(
        operation="deposit", amount=Decimal("10"), protocol="nexapilot-vault", wallet_balance=Decimal("1000")
    )
    assert small_wallet.score > large_wallet.score


def test_risk_assessment_is_deterministic():
    kwargs = dict(operation="execute", amount=Decimal("42"), protocol="MonadLoop", action_type="PROVIDE_LIQUIDITY")
    first = assess_risk(**kwargs)
    second = assess_risk(**kwargs)
    assert first.score == second.score
    assert first.risk_level == second.risk_level


# ---------------------------------------------------------------------
# 2. Policy Engine -- pure unit tests
# ---------------------------------------------------------------------


def _policy(**overrides) -> Policy:
    defaults = dict(
        max_transaction_amount=Decimal("100"),
        daily_limit=Decimal("200"),
        allowed_protocols=[],
        allowed_actions=[],
        max_risk_level=RiskLevel.MEDIUM,
        approval_required=True,
    )
    defaults.update(overrides)
    return Policy(**defaults)


def test_amount_over_max_transaction_amount_is_rejected():
    decision = evaluate_policy(
        policy=_policy(max_transaction_amount=Decimal("50")),
        operation="deposit",
        amount=Decimal("75"),
        protocol="nexapilot-vault",
        action_type=None,
        risk_level=RiskLevel.LOW,
        already_spent_today=Decimal("0"),
    )
    assert decision.passed is False
    assert any(c.rule == "max_transaction_amount" and not c.passed for c in decision.checks)


def test_daily_limit_is_enforced_across_prior_spend():
    decision = evaluate_policy(
        policy=_policy(daily_limit=Decimal("100")),
        operation="deposit",
        amount=Decimal("30"),
        protocol="nexapilot-vault",
        action_type=None,
        risk_level=RiskLevel.LOW,
        already_spent_today=Decimal("80"),  # 80 + 30 = 110 > 100
    )
    assert decision.passed is False
    assert any(c.rule == "daily_limit" and not c.passed for c in decision.checks)


def test_protocol_not_on_allow_list_is_rejected():
    decision = evaluate_policy(
        policy=_policy(allowed_protocols=["nexapilot-vault"]),
        operation="execute",
        amount=Decimal("5"),
        protocol="MonadLoop",
        action_type="PROVIDE_LIQUIDITY",
        risk_level=RiskLevel.LOW,
        already_spent_today=Decimal("0"),
    )
    assert decision.passed is False
    assert any(c.rule == "allowed_protocols" and not c.passed for c in decision.checks)


def test_action_not_on_allow_list_is_rejected():
    decision = evaluate_policy(
        policy=_policy(allowed_actions=["DEPOSIT"]),
        operation="withdraw",
        amount=Decimal("5"),
        protocol="nexapilot-vault",
        action_type=None,
        risk_level=RiskLevel.LOW,
        already_spent_today=Decimal("0"),
    )
    assert decision.passed is False
    assert any(c.rule == "allowed_actions" and not c.passed for c in decision.checks)


def test_empty_allow_lists_mean_no_restriction():
    decision = evaluate_policy(
        policy=_policy(allowed_protocols=[], allowed_actions=[]),
        operation="execute",
        amount=Decimal("5"),
        protocol="AnyProtocolAtAll",
        action_type="ANYTHING",
        risk_level=RiskLevel.LOW,
        already_spent_today=Decimal("0"),
    )
    assert all(c.passed for c in decision.checks if c.rule in ("allowed_protocols", "allowed_actions"))


def test_risk_above_max_risk_level_is_rejected():
    decision = evaluate_policy(
        policy=_policy(max_risk_level=RiskLevel.LOW),
        operation="execute",
        amount=Decimal("5"),
        protocol="MonadLoop",
        action_type="PROVIDE_LIQUIDITY",
        risk_level=RiskLevel.HIGH,
        already_spent_today=Decimal("0"),
    )
    assert decision.passed is False
    assert any(c.rule == "max_risk_level" and not c.passed for c in decision.checks)


def test_passing_decision_with_approval_required_requests_approval():
    decision = evaluate_policy(
        policy=_policy(approval_required=True),
        operation="deposit",
        amount=Decimal("5"),
        protocol="nexapilot-vault",
        action_type=None,
        risk_level=RiskLevel.LOW,
        already_spent_today=Decimal("0"),
    )
    assert decision.passed is True
    assert decision.requires_approval is True


def test_passing_decision_without_approval_required_does_not_request_approval():
    decision = evaluate_policy(
        policy=_policy(approval_required=False),
        operation="deposit",
        amount=Decimal("5"),
        protocol="nexapilot-vault",
        action_type=None,
        risk_level=RiskLevel.LOW,
        already_spent_today=Decimal("0"),
    )
    assert decision.passed is True
    assert decision.requires_approval is False


def test_determine_transaction_status_maps_every_outcome():
    passing = PolicyDecision(passed=True, requires_approval=True, checks=[], reasons=[])
    assert determine_transaction_status(passing) == TransactionStatus.AWAITING_APPROVAL

    passing_no_approval = PolicyDecision(passed=True, requires_approval=False, checks=[], reasons=[])
    assert determine_transaction_status(passing_no_approval) == TransactionStatus.APPROVED

    risk_failed = PolicyDecision(
        passed=False,
        requires_approval=False,
        checks=[PolicyCheckResult(rule="max_risk_level", passed=False, detail="too risky")],
        reasons=["too risky"],
    )
    assert determine_transaction_status(risk_failed) == TransactionStatus.RISK_REJECTED

    policy_failed = PolicyDecision(
        passed=False,
        requires_approval=False,
        checks=[PolicyCheckResult(rule="max_transaction_amount", passed=False, detail="too big")],
        reasons=["too big"],
    )
    assert determine_transaction_status(policy_failed) == TransactionStatus.POLICY_REJECTED


# ---------------------------------------------------------------------
# 3. HTTP-level: standalone /api/v1/risk and /api/v1/policy endpoints
# ---------------------------------------------------------------------


def _connect(client, address: str) -> dict:
    resp = client.post("/api/v1/auth/connect", json={"address": address, "chain": "monad"})
    assert resp.status_code == 200
    auth = resp.json()
    return {"Authorization": f"Bearer {auth['access_token']}"}


def test_risk_assess_endpoint(client, db_session):
    headers = _connect(client, "0xa1a1000000000000000000000000000000000000")
    resp = client.post(
        "/api/v1/risk/assess",
        headers=headers,
        json={"operation": "deposit", "amount": "5", "protocol": "nexapilot-vault"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_level"] == "LOW"
    assert len(body["factors"]) == 6


def test_policy_evaluate_endpoint_passes_within_limits(client, db_session):
    headers = _connect(client, "0xa2a2000000000000000000000000000000000000")
    resp = client.post(
        "/api/v1/policy/evaluate",
        headers=headers,
        json={"operation": "deposit", "amount": "5", "protocol": "nexapilot-vault"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["policy_decision"]["passed"] is True
    assert body["final_status"] == "AWAITING_APPROVAL"  # default policy requires approval


def test_policy_evaluate_endpoint_rejects_amount_over_limit(client, db_session):
    headers = _connect(client, "0xa3a3000000000000000000000000000000000000")
    # Default policy max_transaction_amount is 100 MON (see app/core/config.py).
    resp = client.post(
        "/api/v1/policy/evaluate",
        headers=headers,
        json={"operation": "deposit", "amount": "500", "protocol": "nexapilot-vault"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["policy_decision"]["passed"] is False
    assert body["final_status"] == "POLICY_REJECTED"
    assert any("max transaction amount" in reason for reason in body["policy_decision"]["reasons"])


def test_policy_evaluate_endpoint_rejects_when_risk_exceeds_configured_max(client, db_session):
    headers = _connect(client, "0xa4a4000000000000000000000000000000000000")
    # Tighten the policy to LOW-risk-only, then propose something the Risk
    # Engine will score HIGH.
    resp = client.put(
        "/api/v1/policies/me",
        headers=headers,
        json={
            "max_transaction_amount": "1000",
            "daily_limit": "1000",
            "allowed_protocols": [],
            "allowed_actions": [],
            "max_risk_level": "LOW",
            "approval_required": True,
        },
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/policy/evaluate",
        headers=headers,
        json={"operation": "execute", "amount": "500", "protocol": "MonadLoop", "action_type": "PROVIDE_LIQUIDITY"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_level"] == "HIGH"
    assert body["policy_decision"]["passed"] is False
    assert body["final_status"] == "RISK_REJECTED"


def test_policy_usage_endpoint_starts_at_zero(client, db_session):
    headers = _connect(client, "0xa5a5000000000000000000000000000000000000")
    resp = client.get("/api/v1/policy/usage", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert float(body["spent_today"]) == 0
    assert float(body["remaining_today"]) == float(body["daily_limit"])


# ---------------------------------------------------------------------
# 4. Full pipeline through /api/v1/ai/query: Claude action -> Risk Check
#    -> Policy Check -> PASS/REJECT
# ---------------------------------------------------------------------


def _transaction_plan_message(*, operation, amount, protocol, action_type=None, target_contract=None):
    proposed = {
        "operation": operation,
        "amount": amount,
        "protocol": protocol,
        "reasoning": "Test-driven proposal.",
        "risk_notes": "Claude's own advisory note -- must never affect the actual verdict.",
    }
    if action_type:
        proposed["action_type"] = action_type
    if target_contract:
        proposed["target_contract"] = target_contract
    return _message(
        [
            tool_use(
                "submit_nexapilot_action",
                {
                    "intent": "TRANSACTION_PLAN",
                    "summary": f"{operation} {amount} MON",
                    "explanation": "Test explanation.",
                    "proposed_transaction": proposed,
                },
            )
        ]
    )


def test_ai_transaction_plan_rejected_by_policy_amount(monkeypatch, client, db_session):
    headers = _connect(client, "0xb1b1000000000000000000000000000000000000")
    fake_client = ScriptedAnthropicClient(
        [_transaction_plan_message(operation="deposit", amount=500, protocol="nexapilot-vault")]
    )
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client)

    resp = client.post("/api/v1/ai/query", headers=headers, json={"message": "Deposit 500 MON"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["transaction_status"] == "POLICY_REJECTED"

    tx = client.get(f"/api/v1/transactions/{body['transaction_id']}", headers=headers).json()
    assert tx["status"] == "POLICY_REJECTED"
    assert tx["policy_decision"]["passed"] is False


def test_ai_transaction_plan_rejected_by_risk(monkeypatch, client, db_session):
    headers = _connect(client, "0xb2b2000000000000000000000000000000000000")

    # Tighten this user's policy to LOW-risk-only.
    resp = client.put(
        "/api/v1/policies/me",
        headers=headers,
        json={
            "max_transaction_amount": "1000",
            "daily_limit": "1000",
            "allowed_protocols": [],
            "allowed_actions": [],
            "max_risk_level": "LOW",
            "approval_required": True,
        },
    )
    assert resp.status_code == 200

    fake_client = ScriptedAnthropicClient(
        [
            _transaction_plan_message(
                operation="execute",
                amount=500,
                protocol="MonadLoop",
                action_type="PROVIDE_LIQUIDITY",
                target_contract="0x9999000000000000000000000000000000abcd",
            )
        ]
    )
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client)

    resp = client.post("/api/v1/ai/query", headers=headers, json={"message": "Loop 500 MON into MonadLoop"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_level"] == "HIGH"
    assert body["transaction_status"] == "RISK_REJECTED"


def test_ai_transaction_plan_approved_when_approval_not_required(monkeypatch, client, db_session):
    headers = _connect(client, "0xb3b3000000000000000000000000000000000000")
    resp = client.put(
        "/api/v1/policies/me",
        headers=headers,
        json={
            "max_transaction_amount": "100",
            "daily_limit": "200",
            "allowed_protocols": [],
            "allowed_actions": [],
            "max_risk_level": "MEDIUM",
            "approval_required": False,
        },
    )
    assert resp.status_code == 200

    fake_client = ScriptedAnthropicClient(
        [_transaction_plan_message(operation="deposit", amount=5, protocol="nexapilot-vault")]
    )
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client)

    resp = client.post("/api/v1/ai/query", headers=headers, json={"message": "Deposit 5 MON"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["transaction_status"] == "APPROVED"


def test_daily_limit_is_enforced_across_successive_ai_queries(monkeypatch, client, db_session):
    headers = _connect(client, "0xb4b4000000000000000000000000000000000000")
    resp = client.put(
        "/api/v1/policies/me",
        headers=headers,
        json={
            "max_transaction_amount": "1000",
            "daily_limit": "150",
            "allowed_protocols": [],
            "allowed_actions": [],
            "max_risk_level": "MEDIUM",
            "approval_required": False,
        },
    )
    assert resp.status_code == 200

    # First deposit of 100 MON -- within the 150 MON daily limit.
    fake_client_1 = ScriptedAnthropicClient(
        [_transaction_plan_message(operation="deposit", amount=100, protocol="nexapilot-vault")]
    )
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client_1)
    resp1 = client.post("/api/v1/ai/query", headers=headers, json={"message": "Deposit 100 MON"})
    assert resp1.json()["transaction_status"] == "APPROVED"

    # Second deposit of 100 MON -- 100 + 100 = 200 > 150 MON daily limit.
    fake_client_2 = ScriptedAnthropicClient(
        [_transaction_plan_message(operation="deposit", amount=100, protocol="nexapilot-vault")]
    )
    monkeypatch.setattr(ai_service_module, "get_anthropic_client", lambda: fake_client_2)
    resp2 = client.post("/api/v1/ai/query", headers=headers, json={"message": "Deposit another 100 MON"})
    body2 = resp2.json()
    assert body2["transaction_status"] == "POLICY_REJECTED"

    tx2 = client.get(f"/api/v1/transactions/{body2['transaction_id']}", headers=headers).json()
    assert any("daily limit" in reason for reason in tx2["policy_decision"]["reasons"])
