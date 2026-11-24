# AI Use Log

This log discloses generative AI use in **producing** this project. Runtime AI (the fraud-triage design) is governed separately in [ADR-009](docs/adr/ADR-009-bounded-ai-triage.md).

## Policy

1. Humans own every submitted decision, line of code and claim.
2. No real personal, financial or confidential data may be entered into an AI tool.
3. AI output must be reviewed and, where executable, run before acceptance.
4. AI must not fabricate test results, screenshots, citations or stakeholder feedback.
5. AI use is recorded on the day it occurs, including rejected output.

## Register

| ID | Date | Member | Tool / model | Purpose | Prompt summary | Files affected | Verification performed | Disposition (accepted / modified / rejected) | Reviewer |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| AI-001 | 2026-11-22 | M4 | Claude | Code generation and debugging | FastAPI triage skeleton, FraudAlert models, tests, SQLite locking fixes | `services/ai_triage/main.py`, tests (**not present in this repository at `f987b32`**) | [M4 to complete] | [M4 to complete] | [name] |
| AI-002 | 2026-11-22 | M4 | Claude | Data environment | Seed generator (seed 42) and synthetic-data audit | `scripts/seed.py`, `tests/test_synthetic_data.py` (**not present in this repository at `f987b32`**) | [M4 to complete] | [M4 to complete] | [name] |
| AI-003 | 2026-11-24 | [name] | Claude Opus 5.5 (Claude Code) | Submission documentation | Draft brief, dossier, deck, demo script, evidence outline, README, ADR-005 and ADR-007 to ADR-009 from repository | `README.md`, `AI_USE_LOG.md`, `docs/submission/*`, `docs/adr/ADR-005`, `ADR-007` to `ADR-009` | AI tool ran services and tests in an isolated copy; human review: [to complete] | [to complete] | [name] |
| AI-004 | YYYY-MM-DD | | | | | | | | |

AI-001 and AI-002 are carried forward from `docs/AI_USE_LOG.md`.

## Entry template for material use

```markdown
### AI-XXX: <title>
- Date / member / tool and version:
- Objective:
- Prompt (verbatim or faithful summary):
- Data shared and confirmation that it is synthetic:
- Output used:
- Human changes and reasons:
- Errors or unsupported claims found:
- Verification (commands, tests, sources):
- Final decision and reviewer:
```

## Declaration

We confirm this log is complete and accurate, that we understand the submitted work, and that we accept responsibility for it.

| Member | Student ID | Signature | Date |
| :--- | :--- | :--- | :--- |
| [M1] | | | |
| [M2] | | | |
| [M3] | | | |
| [M4] | | | |
