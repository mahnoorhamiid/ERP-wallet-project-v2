# ADR 006: Outbox Pattern for Event Delivery

## Context
When a state changes (e.g., transfer initiated), we must notify other services. If we save to the database but crash before sending the event, the system becomes inconsistent.

## Decision
We implement the Transactional Outbox pattern. Events are written to an `outbox` table in the same database transaction as the state change. A background dispatcher polls the outbox and sends the events.

## Consequences
- Positive: Guarantees at-least-once delivery. State and events are always consistent.
- Negative: Consumers must be idempotent to handle duplicate events.