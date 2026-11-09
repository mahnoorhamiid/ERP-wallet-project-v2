# Event Catalogue

| Event | Producer | Consumer | Trigger | Key Fields | Dedupe Key | Ordering |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `transfer.initiated` | Gateway | Txn | `POST /v1/transfers` | `transfer_id`, `amount_minor` | `event_id` | None |
| `transfer.state_changed` | Txn | Compliance | State transition | `from_state`, `to_state` | `event_id` | None |
| `rail.settlement_confirmed` | Rail Mock | Txn | Rail callback | `rail_reference`, `status` | `event_id` | None |
| `hold.resolved` | Compliance | Txn | Officer decision | `decision` (RELEASE/REJECT) | `event_id` | None |

**Versioning Rule:** Adding an optional field is a minor change. Anything else is a new major `event_version` and a new schema file.