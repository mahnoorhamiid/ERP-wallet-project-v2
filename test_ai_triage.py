import os
import pytest
import time
import sqlite3
from fastapi.testclient import TestClient
from services.ai_triage.main import app, DB_PATH

client = TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_db(monkeypatch):
    # Force the app to use an in-memory database for tests
    monkeypatch.setenv("AI_DB_PATH", ":memory:")
    # We must re-initialize the DB for the in-memory version
    from services.ai_triage.main import init_db
    init_db()
    yield

def test_ai_returns_recommendation_above_threshold(monkeypatch):
    monkeypatch.setenv("AI_ABSTAIN_THRESHOLD", "0.5")
    payload = {
        "alert_id": "alert-123",
        "transfer_id": "txn-456",
        "amount_minor": 100000,
        "risk_signals": ["AML_ALERT"],
        "correlation_id": "corr-789"
    }
    response = client.post("/internal/v1/triage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["abstained"] is False
    assert data["disposition"] == "REVIEW_REJECT"

def test_ai_abstains_below_threshold(monkeypatch):
    monkeypatch.setenv("AI_ABSTAIN_THRESHOLD", "0.99")
    payload = {
        "alert_id": "alert-999",
        "transfer_id": "txn-999",
        "amount_minor": 100000,
        "risk_signals": [],
        "correlation_id": "corr-999"
    }
    response = client.post("/internal/v1/triage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["abstained"] is True
    assert data["disposition"] == "ABSTAIN"