# M1 Integration Contracts

## Contract Register
All inter-component contracts are tracked in `docs/contracts/CONTRACT_REGISTER.md`. They are frozen at v1.0.

## Event Catalogue
The system uses 4 event types: `transfer.initiated`, `transfer.state_changed`, `rail.settlement_confirmed`, and `hold.resolved`.

## Versioning Rules
- Adding an optional field is a minor change.
- Removing/renaming a field requires a major version bump.
