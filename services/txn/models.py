from datetime import datetime
from sqlalchemy import (String, Integer, BigInteger, ForeignKey, UniqueConstraint,
                        DateTime, Text, Boolean, JSON, Index)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from services.txn.db import Base


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"
    account_id:   Mapped[str] = mapped_column(String(64), primary_key=True)
    name:         Mapped[str] = mapped_column(String(128))
    account_type: Mapped[str] = mapped_column(String(32))   # LIABILITY | ASSET
    wallet_id:    Mapped[str | None] = mapped_column(String(32), nullable=True)

class LedgerJournal(Base):
    __tablename__ = "ledger_journals"
    journal_id:         Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    transfer_id:        Mapped[str] = mapped_column(String(36), index=True)
    leg:                Mapped[str] = mapped_column(String(16))   # DEBIT_LEG | CREDIT_LEG | REVERSAL_LEG | OPENING
    source_event_id:    Mapped[str] = mapped_column(String(36))
    correlation_id:     Mapped[str] = mapped_column(String(36))
    reverses_journal_id:Mapped[str | None] = mapped_column(String(36), nullable=True)
    posted_at:          Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("transfer_id", "leg", name="uq_journal_transfer_leg"),)

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    entry_id:     Mapped[str] = mapped_column(String(36), primary_key=True)
    journal_id:   Mapped[str] = mapped_column(ForeignKey("ledger_journals.journal_id"), index=True)
    account_id:   Mapped[str] = mapped_column(ForeignKey("ledger_accounts.account_id"), index=True)
    direction:    Mapped[str] = mapped_column(String(6))   # DEBIT | CREDIT
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency:     Mapped[str] = mapped_column(String(3), default="PKR")

# ---- Transfer state ----
class Transfer(Base):
    __tablename__ = "txn_transfers"
    transfer_id:         Mapped[str] = mapped_column(String(36), primary_key=True)
    sender_wallet_id:    Mapped[str] = mapped_column(String(32))
    receiver_wallet_id:  Mapped[str] = mapped_column(String(32))
    amount_minor:        Mapped[int] = mapped_column(BigInteger)
    currency:            Mapped[str] = mapped_column(String(3), default="PKR")
    state:               Mapped[str] = mapped_column(String(24), index=True)
    version:             Mapped[int] = mapped_column(Integer, default=0)
    correlation_id:      Mapped[str] = mapped_column(String(36))
    idempotency_key:     Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_reason:      Mapped[str | None] = mapped_column(String(64), nullable=True)
    hold_reason_code:    Mapped[str | None] = mapped_column(String(64), nullable=True)
    recon_flag:          Mapped[bool] = mapped_column(Boolean, default=False)
    created_at:          Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at:          Mapped[datetime] = mapped_column(DateTime(timezone=True))

class StateHistory(Base):
    __tablename__ = "txn_state_history"
    id:           Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transfer_id:  Mapped[str] = mapped_column(String(36), index=True)
    from_state:   Mapped[str] = mapped_column(String(24))
    to_state:     Mapped[str] = mapped_column(String(24))
    reason:       Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_id:     Mapped[str] = mapped_column(String(36))
    occurred_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True))

# ---- Inbox (dedupe) ----
class Inbox(Base):
    __tablename__ = "txn_inbox"
    event_id:        Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type:      Mapped[str] = mapped_column(String(64))
    processed_at:    Mapped[datetime] = mapped_column(DateTime(timezone=True))
    result_snapshot: Mapped[dict] = mapped_column(JSON)

# ---- Recon exception queue ----
class ReconException(Base):
    __tablename__ = "recon_exceptions"
    exception_id:   Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id:         Mapped[str] = mapped_column(String(36))
    transfer_id:    Mapped[str] = mapped_column(String(36))
    type:           Mapped[str] = mapped_column(String(32))
    expected_json:  Mapped[dict] = mapped_column(JSON)
    actual_json:    Mapped[dict] = mapped_column(JSON)
    status:         Mapped[str] = mapped_column(String(16), default="OPEN")
    created_at:     Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_by:    Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_note:Mapped[str | None] = mapped_column(Text, nullable=True)
    __table_args__ = (Index("ix_recon_open_unique", "transfer_id", "type", "status"),)