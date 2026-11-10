# ADR-004: Compensation instead of 2PC for Distributed Transactions

## Context
A transfer involves our internal database (Ledger) and an external Rail (Bank). If we debit the sender, but the Rail rejects the transfer, we cannot simply "rollback" the database because the debit might have already been committed, or external systems might have observed the state change.

## Decision
We will use the **Saga Pattern (Compensation)** instead of Two-Phase Commit (2PC). 
1. We debit the sender and transition to `DEBITED`.
2. If the Rail rejects or times out, we transition to `COMPENSATING`.
3. We post a `REVERSAL_LEG` journal entry to refund the sender.
4. We transition to `REVERSED`.

## Consequences
- **Positive**: High availability. We don't hold database locks while waiting for slow external banks.
- **Positive**: Matches real-world banking practices.
- **Negative**: The money is temporarily in limbo (held in `CLEARING:SETTLEMENT`).
- **Mitigation**: We built a background Recovery Loop that scans for `DEBITED` transfers stuck for more than 10 seconds and automatically queries the rail to resolve them.