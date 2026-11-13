# M2 Database ERD (System of Record)

```mermaid
erDiagram
    TRANSFER ||--o{ LEDGER_JOURNAL : generates
    LEDGER_JOURNAL ||--|{ LEDGER_ENTRY : contains
    LEDGER_ACCOUNT ||--o{ LEDGER_ENTRY : references
    TRANSFER ||--o{ STATE_HISTORY : logs
    TRANSFER {
        string transfer_id PK
        string state
        int amount_minor
        int version
    }
    LEDGER_JOURNAL {
        string journal_id PK
        string transfer_id FK
        string leg "DEBIT_LEG, CREDIT_LEG"
    }
    LEDGER_ENTRY {
        string entry_id PK
        string journal_id FK
        string account_id FK
        string direction "DEBIT, CREDIT"
        int amount_minor
    }
    INBOX {
        string event_id PK
        string event_type
        json result_snapshot
    }