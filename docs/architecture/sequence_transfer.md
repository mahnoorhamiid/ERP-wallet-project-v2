# Sequence Diagram: Happy Path Transfer

```mermaid
sequenceDiagram
    autonumber
    actor Customer
    participant Gateway as M1: Gateway
    participant Txn as M2: Txn Service
    participant Comp as M3: Compliance
    participant Rail as M2: Rail Mock
    participant Ledger as M2: Ledger

    Customer->>Gateway: POST /v1/transfers (Idempotency-Key)
    Gateway->>Gateway: Check Idempotency Table (IN_PROGRESS)
    Gateway->>Txn: POST /internal/v1/events (transfer.initiated)
    
    Txn->>Comp: POST /internal/v1/screen (KYC/AML)
    Comp-->>Txn: ALLOW
    
    Txn->>Ledger: post_debit_leg()
    Ledger-->>Txn: Success (Balance reduced)
    
    Txn->>Rail: POST /rail/v1/settlements
    Rail-->>Txn: SETTLED
    
    Txn->>Ledger: post_credit_leg()
    Ledger-->>Txn: Success (Balance increased)
    
    Txn-->>Gateway: 200 OK (snapshot: COMPLETED)
    Gateway->>Gateway: Update Idempotency Table (COMPLETED)
    Gateway-->>Customer: 201 Created (TransferResponse)