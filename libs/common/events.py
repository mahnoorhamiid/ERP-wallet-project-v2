"""Event envelope and payloads (v1.0).

Every event in the system is wrapped in an EventEnvelope. The `data` field
is typed per event_type. Unknown event_type is rejected.
"""
from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


Currency = Literal["PKR"]


class EventType(str, Enum):
    TRANSFER_INITIATED = "transfer.initiated"
    TRANSFER_STATE_CHANGED = "transfer.state_changed"
    RAIL_SETTLEMENT_CONFIRMED = "rail.settlement_confirmed"
    HOLD_RESOLVED = "hold.resolved"


# ---------- payloads ----------

class TransferInitiatedData(BaseModel):
    transfer_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=64)
    sender_wallet_id: str = Field(pattern=r"^W-[A-Z0-9]{3,12}$")
    receiver_wallet_id: str = Field(pattern=r"^W-[A-Z0-9]{3,12}$")
    amount_minor: int = Field(gt=0)
    currency: Currency = "PKR"
    reference: str | None = Field(default=None, max_length=140)
    channel: str = "customer_app"

    @model_validator(mode="after")
    def _wallets_differ(self):
        if self.sender_wallet_id == self.receiver_wallet_id:
            raise ValueError("sender and receiver wallet must differ")
        return self


class TransferStateChangedData(BaseModel):
    transfer_id: UUID
    from_state: str
    to_state: str
    reason_code: str | None = None
    journal_ids: list[UUID] = Field(default_factory=list)


class RailSettlementConfirmedData(BaseModel):
    transfer_id: UUID
    rail_reference: str
    amount_minor: int = Field(gt=0)
    status: Literal["SETTLED", "REJECTED"]
    settled_at: datetime


class HoldResolvedData(BaseModel):
    transfer_id: UUID
    alert_id: UUID
    decision: Literal["RELEASE", "REJECT"]
    decided_by: str
    decided_at: datetime


# ---------- envelope ----------

class EventEnvelope(BaseModel):
    event_id: UUID
    event_type: EventType
    event_version: str = "1.0"
    occurred_at: datetime
    producer: str
    correlation_id: UUID
    causation_id: UUID | None = None
    data: dict

    @model_validator(mode="after")
    def _validate_data(self):
        model = {
            EventType.TRANSFER_INITIATED: TransferInitiatedData,
            EventType.TRANSFER_STATE_CHANGED: TransferStateChangedData,
            EventType.RAIL_SETTLEMENT_CONFIRMED: RailSettlementConfirmedData,
            EventType.HOLD_RESOLVED: HoldResolvedData,
        }[self.event_type]
        # parse to validate; then store the parsed dict back
        self.data = model(**self.data).model_dump(mode="json")
        return self