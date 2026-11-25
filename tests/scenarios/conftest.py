"""In-process harness shared by the S02-S04 scenarios.

The real Transaction, Compliance and Rail apps run against a temporary SQLite
database, so no servers are needed and the repository's txn.db is untouched.
"""
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import case, create_engine, func, select

from libs.common.outbox import init_outbox
from services.compliance.main import app as compliance_app
from services.rail_mock import main as rail_main
from services.txn import db, ledger, recon
from services.txn import main as txn_main
from services.txn.models import (
    LedgerEntry, LedgerJournal, ReconException, StateHistory, Transfer,
)

SENDER, RECEIVER = "W-DEMO001", "W-DEMO002"
OPENING = {SENDER: 50_000_000, RECEIVER: 10_000_000}

SIGNED_AMOUNT = case((LedgerEntry.direction == "CREDIT", LedgerEntry.amount_minor),
                     else_=-LedgerEntry.amount_minor)


def event(event_type, **data):
    return {"event_id": str(uuid4()), "event_type": event_type,
            "correlation_id": str(uuid4()), "data": data}


def initiated(amount):
    return event("transfer.initiated", transfer_id=str(uuid4()),
                 sender_wallet_id=SENDER, receiver_wallet_id=RECEIVER,
                 amount_minor=amount, currency="PKR")


class WalletSystem:
    """Drives the services over HTTP and reads the resulting database state."""

    def __init__(self):
        self.txn = TestClient(txn_main.app, raise_server_exceptions=False)
        self.compliance = TestClient(compliance_app)
        self.rail = TestClient(rail_main.app)
        self.settle_calls = 0
        self.lose_rail_response = False

    # --- outbound HTTP made by the services, routed to the in-process apps ---
    def _route(self, url):
        for base, client in ((txn_main.RAIL_URL, self.rail),
                             (txn_main.COMPLIANCE_URL, self.compliance)):
            if url.startswith(base):
                return client, url[len(base):]
        raise AssertionError(f"unexpected outbound call: {url}")

    def http_post(self, url, json, timeout=None):
        client, path = self._route(url)
        response = client.post(path, json=json)
        if client is self.rail:
            self.settle_calls += 1
            if self.lose_rail_response:
                raise httpx.ReadTimeout("response lost after the rail processed it")
        return response

    def http_get(self, url, params=None, timeout=None):
        client, path = self._route(url)
        return client.get(path, params=params)

    # --- actions ---
    def send(self, envelope):
        return self.txn.post("/internal/v1/events", json=envelope)

    def transfer(self, amount):
        response = self.send(initiated(amount))
        assert response.status_code == 200, response.text
        return response.json()

    def set_rail_mode(self, mode):
        self.rail.post("/rail/admin/mode", params={"mode": mode}).raise_for_status()

    def inject_break(self, transfer_id, kind):
        self.rail.post("/rail/admin/inject-break",
                       params={"transfer_id": transfer_id, "kind": kind}).raise_for_status()

    # --- observations ---
    def balances(self):
        with db.SessionLocal() as s:
            return {w: ledger.get_balance(s, w) for w in OPENING}

    def settlement_balance(self):
        with db.SessionLocal() as s:
            return s.scalar(select(func.coalesce(func.sum(SIGNED_AMOUNT), 0))
                            .where(LedgerEntry.account_id == ledger.SETTLEMENT))

    def entry_count(self):
        with db.SessionLocal() as s:
            return s.scalar(select(func.count()).select_from(LedgerEntry))

    def get_transfer(self, transfer_id):
        with db.SessionLocal() as s:
            return s.get(Transfer, transfer_id)

    def journals(self, transfer_id):
        """Journals keyed by leg; (transfer_id, leg) is unique in the schema."""
        return {j.leg: j for j in self._rows(LedgerJournal, transfer_id)}

    def states(self, transfer_id):
        return [h.to_state for h in self._rows(StateHistory, transfer_id, StateHistory.id)]

    def exceptions(self, transfer_id):
        return self._rows(ReconException, transfer_id)

    @staticmethod
    def _rows(model, transfer_id, *order_by):
        with db.SessionLocal() as s:
            return s.scalars(select(model).where(model.transfer_id == transfer_id)
                             .order_by(*order_by)).all()


@pytest.fixture
def wallet(tmp_path, monkeypatch):
    """A seeded system with its own database, rail state and report directory."""
    original_engine = db.engine
    engine = create_engine(f"sqlite:///{(tmp_path / 'txn.db').as_posix()}",
                           connect_args={"check_same_thread": False})
    monkeypatch.setattr(db, "engine", engine)
    db.SessionLocal.configure(bind=engine)
    try:
        db.init_db()
        raw = engine.raw_connection()
        init_outbox(raw.dbapi_connection)
        raw.close()
        with db.SessionLocal.begin() as s:
            for wallet_id, amount in OPENING.items():
                ledger.post_opening_balance(s, wallet_id, amount)

        async def no_sleep(_seconds):
            """Rail timeout modes fail immediately instead of after 10 s."""

        monkeypatch.chdir(tmp_path)  # recon writes to ./reports
        monkeypatch.setattr(rail_main, "STORE", {})
        monkeypatch.setattr(rail_main, "MODE", {"mode": "SUCCESS"})
        monkeypatch.setattr(rail_main, "asyncio", SimpleNamespace(sleep=no_sleep))

        system = WalletSystem()
        http = SimpleNamespace(post=system.http_post, get=system.http_get)
        monkeypatch.setattr(txn_main, "httpx", http)
        monkeypatch.setattr(recon, "httpx", http)
        yield system
    finally:
        db.SessionLocal.configure(bind=original_engine)
        engine.dispose()
