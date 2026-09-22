"""
Blockchain endpoint tests.

These hit a REAL chain over JSON-RPC (the local anvil devnet pinned to
Monad's chain id — see contracts/README.md), not a mock, so the ABI
encoding / allow-list / balance-reading code is genuinely exercised. They
skip cleanly if that devnet isn't up rather than failing the whole suite,
since not every environment running `pytest` will have anvil + the
contract deployed.

The full sign -> submit -> confirm loop (which needs a real private key to
sign with) is covered by scripts/dev_e2e_blockchain_test.py instead — that
script is the actual proof of the end-to-end flow; these tests cover the
API-level validation and state-machine behavior around it.
"""

import pytest
from web3 import Web3

from app.blockchain.client import check_rpc_connection, get_web3

requires_rpc = pytest.mark.skipif(
    not check_rpc_connection()["connected"],
    reason="Local Monad-mirroring devnet (anvil) is not reachable — see contracts/README.md",
)


def _connect(client, address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"):
    resp = client.post("/api/v1/auth/connect", json={"address": address, "chain": "monad"})
    assert resp.status_code == 200
    return resp.json()


def _fund(address: str, amount_ether: int = 1000) -> None:
    """Use anvil's dev-only `anvil_setBalance` cheatcode so tests that
    build (and gas-estimate) a real deposit don't need a funded private
    key — we're only checking the prepared tx shape here, never signing."""
    w3 = get_web3()
    w3.provider.make_request(
        "anvil_setBalance", [Web3.to_checksum_address(address), hex(Web3.to_wei(amount_ether, "ether"))]
    )


@requires_rpc
def test_network_status_reports_real_connection(client):
    resp = client.get("/api/v1/blockchain/network")
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert body["chain_id_matches"] is True
    assert body["contract_address"] is not None


@requires_rpc
def test_wallet_balance_reads_native_and_vault_balance(client):
    auth = _connect(client, address="0x111111a1b2c3d4e5f60000000000000000000000")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    wallet_id = auth["wallet"]["id"]

    resp = client.get(f"/api/v1/blockchain/wallets/{wallet_id}/balance", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["address"] == "0x111111a1b2c3d4e5f60000000000000000000000"
    assert float(body["native_balance"]) == 0  # never funded, not one of anvil's default accounts
    assert float(body["vault_balance"]) == 0


@requires_rpc
def test_prepare_deposit_returns_a_well_formed_unsigned_tx(client):
    auth = _connect(client, address="0x222222a1b2c3d4e5f60000000000000000000000")
    _fund(auth["wallet"]["address"])
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    wallet_id = auth["wallet"]["id"]

    resp = client.post(
        "/api/v1/blockchain/transactions/prepare",
        headers=headers,
        json={"wallet_id": wallet_id, "operation": "deposit", "amount": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    tx = body["unsigned_tx"]
    assert tx["value"] == hex(5 * 10**18)
    assert tx["from"].lower() == "0x222222a1b2c3d4e5f60000000000000000000000"
    assert tx["to"]  # the deployed contract address
    assert tx["data"].startswith("0x")


@requires_rpc
def test_prepare_rejects_amount_over_policy_limit(client):
    auth = _connect(client, address="0x333333a1b2c3d4e5f60000000000000000000000")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    wallet_id = auth["wallet"]["id"]

    resp = client.post(
        "/api/v1/blockchain/transactions/prepare",
        headers=headers,
        json={"wallet_id": wallet_id, "operation": "deposit", "amount": 999},  # default policy cap is 100
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "TRANSACTION_REJECTED"


@requires_rpc
def test_prepare_execute_rejects_non_allowlisted_target(client):
    auth = _connect(client, address="0x444444a1b2c3d4e5f60000000000000000000000")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    wallet_id = auth["wallet"]["id"]

    resp = client.post(
        "/api/v1/blockchain/transactions/prepare",
        headers=headers,
        json={
            "wallet_id": wallet_id,
            "operation": "execute",
            "amount": 1,
            "target_contract": "0x000000000000000000000000000000000000dead",
            "protocol": "evil-protocol",
            "action_type": "STAKE",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "TRANSACTION_REJECTED"
    assert "allow-list" in resp.json()["error"]["message"]


@requires_rpc
def test_transaction_state_machine_guards(client):
    auth = _connect(client, address="0x555555a1b2c3d4e5f60000000000000000000000")
    _fund(auth["wallet"]["address"])
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    wallet_id = auth["wallet"]["id"]

    prepared = client.post(
        "/api/v1/blockchain/transactions/prepare",
        headers=headers,
        json={"wallet_id": wallet_id, "operation": "deposit", "amount": 1},
    ).json()
    tx_id = prepared["transaction_id"]

    # submit before approve -> rejected
    resp = client.post(
        f"/api/v1/blockchain/transactions/{tx_id}/submit",
        headers=headers,
        json={"signed_raw_tx": "0xdead"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INVALID_TRANSACTION_STATE"

    # verify before submit -> rejected
    resp = client.post(f"/api/v1/blockchain/transactions/{tx_id}/verify", headers=headers)
    assert resp.status_code == 409

    # approve -> ok
    resp = client.post(f"/api/v1/blockchain/transactions/{tx_id}/approve", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"

    # approve again -> rejected
    resp = client.post(f"/api/v1/blockchain/transactions/{tx_id}/approve", headers=headers)
    assert resp.status_code == 409

    # submit garbage signed tx -> clean 502, not a crash
    resp = client.post(
        f"/api/v1/blockchain/transactions/{tx_id}/submit",
        headers=headers,
        json={"signed_raw_tx": "0xdeadbeef"},
    )
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "TRANSACTION_BROADCAST_FAILED"


@requires_rpc
def test_wallet_ownership_is_enforced(client):
    auth_a = _connect(client, address="0x666666a1b2c3d4e5f60000000000000000000000")
    auth_b = _connect(client, address="0x777777a1b2c3d4e5f60000000000000000000000")

    b_wallet_id = auth_b["wallet"]["id"]
    headers_a = {"Authorization": f"Bearer {auth_a['access_token']}"}

    resp = client.get(f"/api/v1/blockchain/wallets/{b_wallet_id}/balance", headers=headers_a)
    assert resp.status_code == 404
