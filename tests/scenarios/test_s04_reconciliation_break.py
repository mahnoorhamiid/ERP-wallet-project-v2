"""Scenario S04: reconciliation detects, reports and queues ledger/rail breaks."""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from services.rail_mock import main as rail_main
from services.txn.recon import run_recon
from tests.scenarios.conftest import RECEIVER, SENDER

AMOUNT = 1_000_000


@pytest.fixture
def today():
    return datetime.now(timezone.utc).date().isoformat()


def completed_transfer(wallet):
    result = wallet.transfer(AMOUNT)
    assert result["state"] == "COMPLETED"
    return result["transfer_id"]


# --- each builder creates one break and returns its transfer_id ---
def tampered_amount(wallet):
    tid = completed_transfer(wallet)
    wallet.inject_break(tid, "tamper_amount")
    return tid


def settled_one_minor_unit_short(wallet):
    """A genuine rail discrepancy, created without the tamper hook."""
    tid = completed_transfer(wallet)
    rail_main.STORE[tid]["amount_minor"] = AMOUNT - 1
    return tid


def missing_at_rail(wallet):
    tid = completed_transfer(wallet)
    wallet.inject_break(tid, "delete_row")
    return tid


def missing_in_ledger(wallet):
    tid = str(uuid4())
    wallet.rail.post("/rail/v1/settlements", json={
        "transfer_id": tid, "amount_minor": AMOUNT, "currency": "PKR",
        "sender_wallet_id": SENDER, "receiver_wallet_id": RECEIVER,
        "callback_url": "http://unused", "correlation_id": str(uuid4()),
    }).raise_for_status()
    return tid


def reversed_but_settled(wallet):
    wallet.set_rail_mode("REJECT")
    tid = wallet.transfer(AMOUNT)["transfer_id"]
    rail_main.STORE[tid].update(
        status="SETTLED", settled_at=datetime.now(timezone.utc).isoformat())
    return tid


@pytest.mark.parametrize("make_break, break_type", [
    (tampered_amount, "AMOUNT_MISMATCH"),
    (settled_one_minor_unit_short, "AMOUNT_MISMATCH"),
    (missing_at_rail, "MISSING_AT_RAIL"),
    (missing_in_ledger, "MISSING_IN_LEDGER"),
    (reversed_but_settled, "STATUS_MISMATCH"),
])
def test_s04_break_is_detected_reported_and_queued(wallet, today, make_break, break_type):
    tid = make_break(wallet)

    summary = run_recon(today)

    assert (summary["matched"], summary["breaks"]) == (0, 1)
    assert summary["by_type"] == {break_type: 1}

    [queued] = wallet.exceptions(tid)
    assert (queued.type, queued.status) == (break_type, "OPEN")

    expected_row = {"transfer_id": tid, "type": break_type}
    report = Path("reports") / f"recon_{today}"
    assert json.loads(report.with_suffix(".json").read_text()) == {
        "summary": summary, "details": [expected_row]}
    with report.with_suffix(".csv").open(newline="") as f:
        assert list(csv.DictReader(f)) == [expected_row]


def test_s04_clean_day_has_no_breaks(wallet, today):
    tid = completed_transfer(wallet)

    summary = run_recon(today)

    assert (summary["matched"], summary["breaks"]) == (1, 0)
    assert summary["matched_value_minor"] == AMOUNT
    assert wallet.exceptions(tid) == []


def test_s04_break_is_isolated_from_matching_transfers(wallet, today):
    good, bad = completed_transfer(wallet), tampered_amount(wallet)

    summary = run_recon(today)

    assert (summary["matched"], summary["breaks"]) == (1, 1)
    assert wallet.exceptions(good) == []
    assert len(wallet.exceptions(bad)) == 1


def test_s04_rerun_does_not_duplicate_open_exception(wallet, today):
    tid = tampered_amount(wallet)

    first, second = run_recon(today), run_recon(today)

    assert first["breaks"] == second["breaks"] == 1
    [queued] = wallet.exceptions(tid)
    assert queued.run_id == first["run_id"]


def test_s04_recon_never_changes_balances(wallet, today):
    tampered_amount(wallet)
    before = wallet.balances(), wallet.entry_count()

    run_recon(today)

    assert (wallet.balances(), wallet.entry_count()) == before
