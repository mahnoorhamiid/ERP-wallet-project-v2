# Engineering Evidence Pack: Contents and Capture Guide

**Baseline:** commit `f987b32`. Record the final commit hash, operating system, Python version and UTC time beside every capture. Synthetic data only. Never edit output or recreate it by hand.

## 1. Folder structure

```text
evidence/
├── 00_index.md                 # one row per artefact: ID, file, claim, commit, UTC time, owner
├── 01_environment/             # versions, clean clone, commit hash
├── 02_contracts/               # OpenAPI, event examples, contract-test output
├── 03_tests/                   # pytest output and JUnit XML
├── 04_scenarios/               # S01-S05 console output and screenshots
├── 05_ledger_and_state/        # SQL query results
├── 06_reconciliation/          # JSON, CSV, exception-queue rows
├── 07_observability/           # service logs, correlation trace
├── 08_security/                # negative tests, dependency scan, secret scan
├── 09_ai_governance/           # design, isolation and review evidence
└── 10_known_issues/            # failing output retained, linked to dossier limitation IDs
```

## 2. Evidence register

"Result" is what was observed when the baseline was exercised from a clean copy on Windows 11 and Python 3.13 on 2026-11-24.

| ID | Capture | Supports | Result at baseline |
| :--- | :--- | :--- | :--- |
| E01 | `git log --oneline`, `git rev-parse HEAD`, `python --version`, `pip freeze` | Reproducibility | Available |
| E02 | Four services on 8000, 8001, 8002, 8004; `/health` (8000, 8001) and `/ready` (8001) | Runnable system | Available |
| E03 | `docs/contracts/openapi.yaml` and Swagger UI at `/docs` | API-first contract | Available |
| E04 | `pytest tests/test_events.py -v` | Event contracts | 13 passed |
| E05 | `pytest tests/test_idempotency.py tests/test_outbox.py -v` | Idempotency store, outbox write | 4 passed |
| E06 | `pytest tests/scenarios/test_s01_idempotent_retry.py -v` | Client retry (S01) | **Does not parse:** shell command appended to line 52. With that text removed: 3 passed |
| E07 | `python -m tests.test_ledger` | Ledger rules | Passes on an empty database; fails on committed `txn.db` |
| E08 | Normal transfer console, balances before/after | Happy path | COMPLETED |
| E09 | Rail REJECT scenario (S02) | Compensation | REVERSED, net balance change 0 |
| E10 | Duplicate event scenario (S03) | Exactly-one effect | Second call `duplicate`; one debit |
| E11 | Compliance hold scenario (S05) | Hold without posting | ON_HOLD, balance unchanged |
| E12 | Reconciliation scenario (S04) | Break detection | Scripted test **fails** off its hardcoded date 2026-11-10; run with current UTC date it reports AMOUNT_MISMATCH |
| E13 | Client timeout then same-event retry | Recovery | Client timed out; retry returned `duplicate`, REVERSED; net change 0 |
| E14 | `sql/` results from section 3 | Ledger integrity | 0 unbalanced journals |
| E15 | Rail `TIMEOUT_NOT_SETTLED` result, `recon_flag = 1` | Ambiguity handling | REVERSED and flagged |
| E16 | Same key, different body | Misuse rejection | 422 `IDEMPOTENCY_KEY_REUSED` |
| E17 | Missing key; missing token; same wallet; bad amount | Negative tests | Missing key covered by S01; capture the others |
| E18 | Response `X-Correlation-ID` beside the transfer row | Traceability | Per service only; see L-14 |
| E19 | `pip-audit` and `gitleaks` reports | Supply chain, secrets | To be run |
| E20 | AI isolation and abstention tests | AI governance | **Not available:** no AI service or tests in baseline |
| E21 | `docker compose ps`, network inspection, PostgreSQL run | Deployment | **Not available:** no Docker files in baseline |
| E22 | Contribution log, commit history, AI use log | Academic integrity | Partial: contribution log lists one member |

## 3. Ledger and state queries

Save each query with its result. Use DB Browser for SQLite or the `sqlite3` CLI against `txn.db`.

```sql
-- Expect no rows: every journal balances
SELECT journal_id FROM ledger_entries GROUP BY journal_id
HAVING SUM(CASE direction WHEN 'DEBIT' THEN amount_minor ELSE -amount_minor END) <> 0;

-- Expect no rows: no leg posted twice
SELECT transfer_id, leg, COUNT(*) FROM ledger_journals GROUP BY 1, 2 HAVING COUNT(*) > 1;

-- Full audit trail of one transfer
SELECT from_state, to_state, reason, occurred_at FROM txn_state_history
WHERE transfer_id = '<TRANSFER_ID>' ORDER BY id;

-- Both legs of one transfer
SELECT j.leg, e.account_id, e.direction, e.amount_minor
FROM ledger_journals j JOIN ledger_entries e USING (journal_id)
WHERE j.transfer_id = '<TRANSFER_ID>';

-- Reconciliation queue
SELECT transfer_id, type, status, created_at FROM recon_exceptions ORDER BY created_at DESC;

-- Outbox backlog (expected at baseline: rows stay PENDING; see L-10)
SELECT status, COUNT(*) FROM gw_outbox GROUP BY status;
```

## 4. Capture commands

Run from a **clean clone** in PowerShell with the virtual environment active.

```powershell
New-Item -ItemType Directory -Force evidence\01_environment, evidence\03_tests, evidence\07_observability
git rev-parse HEAD | Out-File evidence\01_environment\commit.txt
pip freeze | Out-File evidence\01_environment\pip_freeze.txt
pytest tests/test_events.py tests/test_idempotency.py tests/test_outbox.py -v --junitxml=evidence\03_tests\unit.xml | Tee-Object evidence\03_tests\unit.txt
```

To retain logs, start each service with `*> evidence\07_observability\<service>.log` appended.

## 5. Required screenshots

1. Four terminals with the services running.
2. Swagger UI showing `POST /v1/transfers`.
3. Normal transfer with before and after balances.
4. Gateway replay showing the same `transfer_id` and `Idempotent-Replayed: true`.
5. Client timeout followed by the `duplicate` response.
6. Rail rejection with REVERSED and restored balance.
7. State history for the reversed transfer.
8. Compliance hold with unchanged balance.
9. Reconciliation JSON and the OPEN exception row.
10. Test summary with visible commit hash.

## 6. Pre-submission checklist

- [ ] E06, E07 and E12 fixed, or disclosed under `10_known_issues`
- [ ] E20 and E21 delivered, or described everywhere as design only
- [ ] `reports/recon_2026-11-10.*` labelled historical: its 7 MISSING_AT_RAIL rows can arise when the in-memory rail mock restarts
- [ ] All four members recorded in `docs/CONTRIBUTIONS.md`
- [ ] Every index row maps to a claim in the dossier or deck
- [ ] No secrets, real names, phone numbers or CNICs in any capture
