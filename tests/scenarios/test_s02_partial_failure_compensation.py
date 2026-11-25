"""Scenario S02: a transfer that fails after the debit is compensated."""
import pytest

from tests.scenarios.conftest import OPENING, RECEIVER, SENDER

AMOUNT = 1_000_000


@pytest.mark.parametrize("mode, recon_flag", [
    ("REJECT", False),
    ("TIMEOUT_NOT_SETTLED", True),  # outcome unconfirmed, so flagged for recon
])
def test_s02_rail_failure_refunds_sender(wallet, mode, recon_flag):
    wallet.set_rail_mode(mode)

    result = wallet.transfer(AMOUNT)

    tid = result["transfer_id"]
    assert result["state"] == "REVERSED"
    assert wallet.states(tid) == ["SCREENING", "DEBITED", "COMPENSATING", "REVERSED"]
    assert wallet.get_transfer(tid).recon_flag is recon_flag
    assert wallet.balances() == OPENING
    assert wallet.settlement_balance() == 0


def test_s02_reversal_is_a_new_journal_linked_to_the_debit(wallet):
    wallet.set_rail_mode("REJECT")

    journals = wallet.journals(wallet.transfer(AMOUNT)["transfer_id"])

    assert journals.keys() == {"DEBIT_LEG", "REVERSAL_LEG"}
    assert (journals["REVERSAL_LEG"].reverses_journal_id
            == journals["DEBIT_LEG"].journal_id)


def test_s02_lost_response_completes_when_inquiry_confirms_settlement(wallet):
    wallet.lose_rail_response = True

    result = wallet.transfer(AMOUNT)

    assert result["state"] == "COMPLETED"
    assert wallet.journals(result["transfer_id"]).keys() == {"DEBIT_LEG", "CREDIT_LEG"}
    assert wallet.balances() == {SENDER: OPENING[SENDER] - AMOUNT,
                                 RECEIVER: OPENING[RECEIVER] + AMOUNT}
    assert wallet.settlement_balance() == 0


def test_s02_next_transfer_succeeds_after_rail_recovers(wallet):
    wallet.set_rail_mode("REJECT")
    assert wallet.transfer(AMOUNT)["state"] == "REVERSED"

    wallet.set_rail_mode("SUCCESS")

    assert wallet.transfer(AMOUNT)["state"] == "COMPLETED"
    assert wallet.balances()[SENDER] == OPENING[SENDER] - AMOUNT
