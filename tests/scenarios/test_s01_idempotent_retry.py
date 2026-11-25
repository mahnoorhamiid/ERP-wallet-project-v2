"""Scenario S01: client retry returns prior status without double debit."""
from fastapi.testclient import TestClient
from services.gateway.main import app

client = TestClient(app)

def _body():
    return {
        "sender_wallet_id": "W-ALICE01",
        "receiver_wallet_id": "W-BOB0001",
        "amount_minor": 100000,
        "currency": "PKR",
    }

def test_s01_client_retry_returns_prior_status_without_double_debit():
    headers = {
        "Idempotency-Key": "s01-test-key-12345",
        "Authorization": "Bearer fake-token"
    }
    
    # First request
    r1 = client.post("/v1/transfers", json=_body(), headers=headers)
    assert r1.status_code == 201
    t1 = r1.json()["transfer_id"]
    
    # Second request (same key, same body)
    r2 = client.post("/v1/transfers", json=_body(), headers=headers)
    assert r2.status_code == 201
    assert r2.json()["transfer_id"] == t1
    assert r2.headers.get("Idempotent-Replayed") == "true"

def test_same_key_different_body_returns_422_key_reused():
    headers = {
        "Idempotency-Key": "s01-test-key-9999",
        "Authorization": "Bearer fake-token"
    }
    
    # First request
    client.post("/v1/transfers", json=_body(), headers=headers)
    
    # Second request (different body)
    bad_body = _body()
    bad_body["amount_minor"] = 5000
    r2 = client.post("/v1/transfers", json=bad_body, headers=headers)
    
    assert r2.status_code == 422
    assert r2.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"

def test_missing_idempotency_key_returns_400():
    r = client.post("/v1/transfers", json=_body(), headers={"Authorization": "Bearer fake"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "MISSING_IDEMPOTENCY_KEY"