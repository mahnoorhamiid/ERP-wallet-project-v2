# Transfer State Machine

The lifecycle of a transfer is strictly controlled by a state machine. Illegal transitions (e.g., jumping from INITIATED directly to COMPLETED) are rejected by the code.

## State Diagram
```mermaid
stateDiagram-v2
    [*] --> INITIATED
    INITIATED --> SCREENING
    INITIATED --> FAILED : WALLET_NOT_FOUND
    
    SCREENING --> DEBITED : ALLOW
    SCREENING --> ON_HOLD : HOLD
    SCREENING --> REJECTED : REJECT
    SCREENING --> FAILED : SCREENING_UNAVAILABLE / INSUFFICIENT_FUNDS
    
    ON_HOLD --> DEBITED : RELEASE
    ON_HOLD --> REJECTED : REJECT
    ON_HOLD --> FAILED : INSUFFICIENT_FUNDS
    
    DEBITED --> COMPLETED : SETTLED
    DEBITED --> COMPENSATING : REJECTED / TIMEOUT_UNCONFIRMED
    
    COMPENSATING --> REVERSED : REVERSAL_POSTED
    
    COMPLETED --> [*]
    REVERSED --> [*]
    REJECTED --> [*]
    FAILED --> [*]