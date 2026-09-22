"""Smoke tests for the read-only scaffolding endpoints (wallets/transactions/activity)."""


def _auth_headers(client, address="0x333333333333333333333333333333333333dddd"):
    token = client.post("/api/v1/auth/connect", json={"address": address}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_wallets_returns_the_connected_wallet(client):
    headers = _auth_headers(client)
    response = client.get("/api/v1/wallets", headers=headers)
    assert response.status_code == 200
    wallets = response.json()
    assert len(wallets) == 1
    assert wallets[0]["is_primary"] is True


def test_transactions_and_activity_start_empty(client):
    headers = _auth_headers(client, address="0x444444444444444444444444444444444444eeee")
    tx_response = client.get("/api/v1/transactions", headers=headers)
    activity_response = client.get("/api/v1/activity", headers=headers)

    assert tx_response.status_code == 200 and tx_response.json() == []
    assert activity_response.status_code == 200 and activity_response.json() == []


def test_get_nonexistent_transaction_returns_404(client):
    headers = _auth_headers(client, address="0x555555555555555555555555555555555555ffff")
    response = client.get(
        "/api/v1/transactions/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_update_policy(client):
    headers = _auth_headers(client, address="0x666666666666666666666666666666666666aaaa")
    response = client.put(
        "/api/v1/policies/me",
        headers=headers,
        json={
            "max_transaction_amount": 250,
            "daily_limit": 500,
            "allowed_protocols": ["aave"],
            "allowed_actions": ["SWAP"],
            "max_risk_level": "LOW",
            "approval_required": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert float(body["max_transaction_amount"]) == 250
    assert body["allowed_protocols"] == ["aave"]
