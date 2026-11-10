
# ADR-003: Double-Entry Ledger for Money Movement

## Context
We need to track user wallet balances accurately. Simple CRUD updates (`UPDATE wallets SET balance = balance - 100`) are prone to race conditions, lost updates, and leave no audit trail if money disappears.

## Decision
We will implement a strict double-entry accounting ledger. 
Every movement of money will be recorded as a `LedgerJournal` containing two or more `LedgerEntries` (one DEBIT, one CREDIT) that must sum to zero. Balances will be calculated by summing the credits and subtracting the debits. 

## Consequences
- **Positive**: Perfect auditability. If money exists in a wallet, there is a matching journal entry proving where it came from.
- **Positive**: Immutability. We never update balances directly; we append new entries.
- **Negative**: Slightly more complex queries to calculate balances (requires `GROUP BY` and `SUM`). 
- **Mitigation**: We can add a materialized view or cached balance column later if performance degrades, but for now, derived balances are safest.