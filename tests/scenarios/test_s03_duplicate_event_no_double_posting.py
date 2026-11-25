"""Scenario S03: at-least-once delivery never posts to the ledger twice."""
from uuid import uuid4

import pytest

from tests.scenarios.conftest import OPENING, RECEIVER, SENDER, event, initiated

AMOUNT = 500_000
AFTER_ONE_TRANSFER = {SENDER: OPENING[SENDER] - AMOUNT,
                      RECEIVER: OPENING[RECEIVER] + AMOUNT}


@pytest.mark.parametrize("mode, state, balances", [
    ("SUCCESS", "COMPLETED", AFTER_ONE_TRANSFER),
    ("REJECT", "REVERSED", OPENING),
])
def test_s03_redelivered_event_has_exactly_one_effect(wallet, mode, state, balances):
    wallet.set_rail_mode(mode)
    envelope = initiated(AMOUNT)
    first = wallet.send(envelope).json()
    assert first["state"] == state
    entries = wallet.entry_count()

    for _ in range(3):
        assert wallet.send(envelope).json() == {"status": "duplicate", "snapshot": first}

    assert wallet.entry_count() == entries
    assert wallet.balances() == balances
    assert wallet.settle_calls == 1


def test_s03_same_transfer_under_new_event_id_is_not_posted_again(wallet):
    envelope = initiated(AMOUNT)
    tid = wallet.send(envelope).json()["transfer_id"]
    stored = wallet.txn.get(f"/internal/v1/transfers/{tid}").json()
    entries = wallet.entry_count()

    response = wallet.send({**envelope, "event_id": str(uuid4())})

    assert response.status_code == 200
    assert response.json() == stored
    assert wallet.entry_count() == entries
    assert wallet.balances() == AFTER_ONE_TRANSFER
    assert wallet.settle_calls == 1


def test_s03_reused_transfer_id_with_different_amount_is_rejected(wallet):
    envelope = initiated(AMOUNT)
    wallet.send(envelope)
    entries = wallet.entry_count()

    response = wallet.send({**envelope, "event_id": str(uuid4()),
                            "data": {**envelope["data"], "amount_minor": AMOUNT + 1}})

    assert response.status_code == 409
    assert response.json()["detail"] == "TRANSFER_ID_CONFLICT"
    assert wallet.entry_count() == entries


def test_s03_late_settlement_callback_does_not_credit_twice(wallet):
    tid = wallet.transfer(AMOUNT)["transfer_id"]
    entries = wallet.entry_count()
    callback = event("rail.settlement_confirmed", transfer_id=tid,
                     amount_minor=AMOUNT, status="SETTLED")

    assert wallet.send(callback).json()["state"] == "COMPLETED"
    assert wallet.send(callback).json()["status"] == "duplicate"

    assert wallet.entry_count() == entries
    assert wallet.balances() == AFTER_ONE_TRANSFER


def test_s03_distinct_events_are_both_processed(wallet):
    """Deduplication must not swallow genuinely different transfers."""
    for _ in range(2):
        assert wallet.transfer(AMOUNT)["state"] == "COMPLETED"

    assert wallet.balances()[SENDER] == OPENING[SENDER] - 2 * AMOUNT
