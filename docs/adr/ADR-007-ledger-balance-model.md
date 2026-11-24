# ADR-007: Ledger Balance Model

**Status:** Proposed for team ratification | **Date:** 2026-11-24 | **Refines:** ADR-003

## Context
ADR-003 selects double-entry accounting. This decision determines how available balance is represented and where funds sit between debit and settlement.

## Options considered
1. **Mutable balance column:** fast, but vulnerable to lost updates and weak audit.
2. **Derived balance from append-only entries:** authoritative, with increasing read cost.
3. **Entries plus a transactionally maintained balance projection:** fast and lockable, with projection-drift risk.

## Decision
Use option 2 for the prototype, with integer paisa and a `CLEARING:SETTLEMENT` account for in-flight funds. A transfer posts `DEBIT_LEG`, then `CREDIT_LEG` or `REVERSAL_LEG`. Each `(transfer_id, leg)` is unique. Corrections are new journals. Move to option 3 in production, with a row lock per wallet and a continuous check of projection against entries.

## Consequences
- **Positive:** a balance is explainable from journals; in-flight exposure is visible; reversals preserve history.
- **Negative:** balance reads grow with history.
- **Hardening required:** the balance check and debit are not serialised by a wallet lock, so concurrent debits can overdraw on PostgreSQL. Immutability is by convention until database privileges or triggers enforce it. The clearing account must be created explicitly: SQLite does not enforce the missing foreign key by default, PostgreSQL would.

## Verification
After a mixed run of normal, rejected and timed-out transfers, the unbalanced-journal query returned zero rows.
