"""Contract tests: valid examples pass, invalid examples fail."""
import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from libs.common.events import EventEnvelope

EXAMPLES = Path(__file__).parent.parent / "docs" / "contracts" / "events" / "examples"

def _load(name):
    return json.loads((EXAMPLES / name).read_text())

@pytest.mark.parametrize("name", [
    "transfer.initiated_valid_1.json",
    "transfer.state_changed_valid_1.json",
    "rail.settlement_confirmed_valid_1.json",
    "hold.resolved_valid_1.json",
])
def test_valid_examples_pass(name):
    EventEnvelope(**_load(name))

@pytest.mark.parametrize("name", [
    "transfer.initiated_invalid_amount.json",
    "transfer.initiated_invalid_same_wallet.json",
    "transfer.state_changed_invalid_missing_fields.json",
    "transfer.state_changed_invalid_transfer_id.json",
    "rail.settlement_confirmed_invalid_status.json",
    "rail.settlement_confirmed_invalid_amount.json",
    "hold.resolved_invalid_decision.json",
    "hold.resolved_invalid_missing_decided_by.json",
])
def test_invalid_examples_fail(name):
    with pytest.raises(ValidationError):
        EventEnvelope(**_load(name))

def test_envelope_rejects_unknown_event_type():
    payload = _load("transfer.initiated_valid_1.json")
    payload["event_type"] = "transfer.unknown"
    with pytest.raises(ValidationError):
        EventEnvelope(**payload)