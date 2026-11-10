
This explains the double-entry accounting.

```markdown
# Ledger Posting Rules

We use a strict double-entry accounting system. Every journal must have balanced debits and credits.

## Chart of Accounts
- `CLEARING:OPENING`: The genesis account. Infinite money.
- `CLEARING:SETTLEMENT`: The intermediary account holding funds during transit.
- `WALLET:<id>`: User liability accounts.

## Posting Examples (Amount: 1000 PKR)

### 1. Opening Balance (Seeding)
- DEBIT `CLEARING:OPENING` (1000)
- CREDIT `WALLET:W-DEMO001` (1000)

### 2. Transfer Initiated (Debit Leg)
- DEBIT `WALLET:W-DEMO001` (1000)
- CREDIT `CLEARING:SETTLEMENT` (1000)

### 3. Transfer Settled (Credit Leg)
- DEBIT `CLEARING:SETTLEMENT` (1000)
- CREDIT `WALLET:W-DEMO002` (1000)

### 4. Transfer Reversed (Compensation)
- DEBIT `CLEARING:SETTLEMENT` (1000)
- CREDIT `WALLET:W-DEMO001` (1000)