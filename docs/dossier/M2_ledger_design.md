# M2 Ledger Design & Accounting Model

## 1. Core Principles
- **Strict Double-Entry**: Every journal entry must have matching debits and credits. The system rejects any journal where `SUM(DEBIT) != SUM(CREDIT)`.
- **Immutability**: Ledger entries are append-only. We never `UPDATE` or `DELETE` a ledger entry. If a mistake is made or a transfer fails, we post a reversing entry (Compensating Transaction).
- **Integer Math**: All amounts are stored as minor units (paisa) as integers to prevent floating-point rounding errors (e.g., `1000000` paisa instead of `10000.00` PKR).
- **Derived Balances**: We do not store wallet balances in a single column. The balance is calculated on the fly using `SUM(credits) - SUM(debits)` against the ledger entries to ensure it matches the journals exactly.

## 2. Chart of Accounts
| Account ID | Type | Description |
| :--- | :--- | :--- |
| `CLEARING:OPENING` | ASSET | The genesis account used to seed demo wallets with initial capital. |
| `CLEARING:SETTLEMENT` | ASSET | Holds funds in transit between the sender's debit and the receiver's credit. |
| `WALLET:<id>` | LIABILITY | User wallets representing their available balance. |

## 3. Journal Legs & Posting Rules
A standard transfer consists of two distinct journal entries (Legs):
1. **DEBIT_LEG**: Deducts from sender's wallet, credits the settlement account. (This happens when compliance approves).
2. **CREDIT_LEG**: Debits the settlement account, credits the receiver's wallet. (This happens when the Rail confirms settlement).
*Note: If the Rail fails, a **REVERSAL_LEG** is created to debit the settlement account and credit the sender's wallet back (Refund).*

## 4. Idempotency & Concurrency
Journals are protected by a unique constraint on `(transfer_id, leg)`. If a network retry happens, the `post_journal` function detects the existing journal and returns it instead of creating a duplicate. 
We use `SELECT ... FOR UPDATE` (or SQLite's implicit locking) when calculating balances to prevent race conditions during concurrent transfers.