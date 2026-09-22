"""
DEV/TEST-ONLY end-to-end harness for the Phase 2 blockchain flow.

This is NOT part of the API or production code path. It exists because
Phase 5/6 (frontend + wallet) don't exist yet, but the project rules
require proving the full flow: backend -> Monad contract -> transaction ->
verification -> database. Something has to sign transactions client-side
to exercise /submit, and in production that's the user's own wallet
(Privy/wagmi/viem) — never the backend. Here, a local anvil dev account
plays that role instead, entirely in this standalone script.

Usage (with the API server and a local anvil devnet already running):
    python scripts/dev_e2e_blockchain_test.py
"""

import json
import os
import sys
import time
from pathlib import Path

import httpx
from eth_account import Account

API_BASE = os.environ.get("NEXAPILOT_API_BASE", "http://127.0.0.1:8000/api/v1")
# Anvil's well-known default account #1 — a local devnet key, never used
# anywhere real funds could reach it.
TEST_PRIVATE_KEY = os.environ.get(
    "NEXAPILOT_TEST_PRIVATE_KEY",
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_DEPLOYMENT = json.loads((REPO_ROOT / "contracts" / "deployments" / "local.json").read_text())
MOCK_PROTOCOL_ADDRESS = LOCAL_DEPLOYMENT["auxiliaryFixtures"]["mockProtocol"]["address"]


def log(msg: str) -> None:
    print(f"\n>>> {msg}")


def sign(unsigned_tx: dict, private_key: str) -> str:
    """Convert the API's hex-string tx fields back to ints and sign it."""
    tx = {
        "to": unsigned_tx["to"],
        "data": unsigned_tx["data"],
        "value": int(unsigned_tx["value"], 16),
        "nonce": int(unsigned_tx["nonce"], 16),
        "chainId": int(unsigned_tx["chainId"], 16),
        "gas": int(unsigned_tx["gas"], 16),
    }
    if unsigned_tx.get("maxFeePerGas"):
        tx["maxFeePerGas"] = int(unsigned_tx["maxFeePerGas"], 16)
        tx["maxPriorityFeePerGas"] = int(unsigned_tx["maxPriorityFeePerGas"], 16)
        tx["type"] = 2
    else:
        tx["gasPrice"] = int(unsigned_tx["gasPrice"], 16)
        tx["type"] = 0

    acct = Account.from_key(private_key)
    signed = acct.sign_transaction(tx)
    return "0x" + signed.raw_transaction.hex().removeprefix("0x")


def run_operation(client: httpx.Client, headers: dict, wallet_id: str, private_key: str, **prepare_body) -> dict:
    log(f"prepare: {prepare_body}")
    resp = client.post(
        f"{API_BASE}/blockchain/transactions/prepare",
        json={"wallet_id": wallet_id, **prepare_body},
        headers=headers,
    )
    resp.raise_for_status()
    prepared = resp.json()
    tx_id = prepared["transaction_id"]
    print(f"    transaction_id={tx_id}")

    resp = client.post(f"{API_BASE}/blockchain/transactions/{tx_id}/approve", headers=headers)
    resp.raise_for_status()
    print(f"    approved -> status={resp.json()['status']}")

    signed_raw_tx = sign(prepared["unsigned_tx"], private_key)
    resp = client.post(
        f"{API_BASE}/blockchain/transactions/{tx_id}/submit",
        json={"signed_raw_tx": signed_raw_tx},
        headers=headers,
    )
    resp.raise_for_status()
    submitted = resp.json()
    print(f"    submitted -> tx_hash={submitted['tx_hash']}")

    for attempt in range(10):
        time.sleep(1)
        resp = client.post(f"{API_BASE}/blockchain/transactions/{tx_id}/verify", headers=headers)
        resp.raise_for_status()
        result = resp.json()
        print(f"    verify attempt {attempt + 1}: status={result['status']} message={result['message']}")
        if result["status"] in ("CONFIRMED", "FAILED"):
            return result

    raise TimeoutError(f"Transaction {tx_id} was not mined in time.")


def main() -> None:
    account = Account.from_key(TEST_PRIVATE_KEY)
    address = account.address
    log(f"Using test wallet {address} (local anvil dev account — never a real wallet)")

    with httpx.Client(timeout=30) as client:
        log("network status")
        resp = client.get(f"{API_BASE}/blockchain/network")
        resp.raise_for_status()
        print("   ", resp.json())

        log("connect wallet")
        resp = client.post(f"{API_BASE}/auth/connect", json={"address": address, "chain": "monad"})
        resp.raise_for_status()
        auth = resp.json()
        token = auth["access_token"]
        wallet_id = auth["wallet"]["id"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"    user_id={auth['user']['id']} wallet_id={wallet_id}")

        log("balance before")
        resp = client.get(f"{API_BASE}/blockchain/wallets/{wallet_id}/balance", headers=headers)
        resp.raise_for_status()
        print("   ", resp.json())

        deposit_result = run_operation(
            client, headers, wallet_id, TEST_PRIVATE_KEY,
            operation="deposit", amount="10", protocol="nexapilot-vault",
        )
        assert deposit_result["status"] == "CONFIRMED", "deposit did not confirm"

        log("balance after deposit")
        resp = client.get(f"{API_BASE}/blockchain/wallets/{wallet_id}/balance", headers=headers)
        resp.raise_for_status()
        print("   ", resp.json())

        execute_result = run_operation(
            client, headers, wallet_id, TEST_PRIVATE_KEY,
            operation="execute", amount="3", protocol="mock-protocol",
            action_type="STAKE", target_contract=MOCK_PROTOCOL_ADDRESS, calldata="0x",
        )
        assert execute_result["status"] == "CONFIRMED", "execute did not confirm"

        log("balance after execute (vault should be 10 - 3 = 7)")
        resp = client.get(f"{API_BASE}/blockchain/wallets/{wallet_id}/balance", headers=headers)
        resp.raise_for_status()
        print("   ", resp.json())

        withdraw_result = run_operation(
            client, headers, wallet_id, TEST_PRIVATE_KEY,
            operation="withdraw", amount="7", protocol="nexapilot-vault",
        )
        assert withdraw_result["status"] == "CONFIRMED", "withdraw did not confirm"

        log("balance after withdraw (vault should be back to 0)")
        resp = client.get(f"{API_BASE}/blockchain/wallets/{wallet_id}/balance", headers=headers)
        resp.raise_for_status()
        print("   ", resp.json())

        log("transactions persisted in the database")
        resp = client.get(f"{API_BASE}/transactions", headers=headers)
        resp.raise_for_status()
        for tx in resp.json():
            print(f"    {tx['action_type']:10s} {tx['status']:10s} {tx['amount_in']} MON  tx={tx['tx_hash']}")

        log("activity feed persisted in the database")
        resp = client.get(f"{API_BASE}/activity", headers=headers)
        resp.raise_for_status()
        for item in resp.json():
            print(f"    {item['title']}: {item['description']}")

    log("ALL PHASE 2 CHECKS PASSED")


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPStatusError as exc:
        print(f"\nHTTP ERROR {exc.response.status_code}: {exc.response.text}", file=sys.stderr)
        raise
