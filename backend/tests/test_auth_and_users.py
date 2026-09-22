def _connect(client, address="0x111111111111111111111111111111111111aaaa"):
    return client.post("/api/v1/auth/connect", json={"address": address, "chain": "monad"})


def test_connect_wallet_creates_user_wallet_and_default_policy(client):
    response = _connect(client)
    assert response.status_code == 200
    body = response.json()

    assert body["access_token"]
    assert body["user"]["risk_preference"] == "MEDIUM"
    assert body["wallet"]["address"] == "0x111111111111111111111111111111111111aaaa"
    assert body["wallet"]["chain"] == "monad"

    token = body["access_token"]
    policy_resp = client.get("/api/v1/policies/me", headers={"Authorization": f"Bearer {token}"})
    assert policy_resp.status_code == 200
    policy = policy_resp.json()
    assert float(policy["max_transaction_amount"]) == 100
    assert float(policy["daily_limit"]) == 200
    assert policy["approval_required"] is True


def test_connect_wallet_is_idempotent_and_normalizes_case(client):
    first = _connect(client, address="0xAAAAAA111111111111111111111111111111BBBB")
    second = _connect(client, address="0xaaaaaa111111111111111111111111111111bbbb")

    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["user"]["id"] == second.json()["user"]["id"]


def test_protected_route_requires_bearer_token(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_token_is_rejected(client):
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_get_and_update_current_user(client):
    token = _connect(client, address="0x222222222222222222222222222222222222cccc").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["display_name"] is None

    updated = client.patch(
        "/api/v1/users/me", headers=headers, json={"display_name": "Test User", "risk_preference": "HIGH"}
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Test User"
    assert updated.json()["risk_preference"] == "HIGH"


def test_connect_validation_rejects_short_address(client):
    response = client.post("/api/v1/auth/connect", json={"address": "ab"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
