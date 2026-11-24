# Technical Demo Script

**Target:** about 9 minutes | **Data:** synthetic | **Shell:** Windows PowerShell 5.1

## Before recording

1. Use a fresh clone and complete README setup. Move `txn.db` aside, then run `python -m services.txn.seed`.
2. Start the four services in separate terminals.
3. Open a fifth terminal in the repository and activate the environment.
4. Rehearse once, then repeat steps 1 and 2 for clean opening balances.
5. Load these helpers:

```powershell
$T="http://127.0.0.1:8001"; $R="http://127.0.0.1:8004"; $G="http://127.0.0.1:8000"
$env:PYTHONIOENCODING="utf-8"
function Get-Bal($w){ (Invoke-RestMethod "$T/internal/v1/wallets/$w/balance").balance_minor }
function New-Transfer($amount){ @{event_id=[guid]::NewGuid().ToString(); event_type="transfer.initiated"; correlation_id=[guid]::NewGuid().ToString(); data=@{transfer_id=[guid]::NewGuid().ToString(); sender_wallet_id="W-DEMO001"; receiver_wallet_id="W-DEMO002"; amount_minor=$amount; currency="PKR"}} }
function Send-Event($e,$timeout=30){ Invoke-RestMethod -Method Post "$T/internal/v1/events" -ContentType "application/json" -Body ($e|ConvertTo-Json -Depth 5) -TimeoutSec $timeout }
function Set-Rail($m){ Invoke-RestMethod -Method Post "$R/rail/admin/mode?mode=$m" }
```

Do not press Enter twice on a transfer: each `New-Transfer` creates a new instruction.

---

## 0:00–1:00 | Introduction

**Show:** README architecture diagram.

**Say:** "This is our digital-wallet prototype, inspired by services such as SadaPay and NayaPay. All wallets and transactions are synthetic. Our selected journey is a wallet-to-wallet transfer. The goal is simple to state: one instruction must have one financial effect, even when networks fail.

The Gateway handles the public API and idempotency. The Transaction Service owns the state machine and double-entry ledger. Compliance and the settlement rail are mocks. In this baseline, the Gateway's call to the Transaction Service is stubbed, so we will show Gateway idempotency first and then drive the ledger through the Transaction Service's event contract. AI triage, Docker and PostgreSQL are designed but not part of today's run."

## 1:00–1:40 | System readiness

```powershell
Invoke-RestMethod "$G/health"; Invoke-RestMethod "$T/ready"
Set-Rail SUCCESS
"Sender: $(Get-Bal W-DEMO001)  Receiver: $(Get-Bal W-DEMO002)"
```

**Expect:** sender 50000000, receiver 10000000.

**Say:** "The services are ready. Amounts are integer paisa, so 50 million paisa is 500,000 rupees. Balances are derived from ledger entries; there is no editable balance column.

We start from a freshly seeded database so that every number you see can be traced to this recording. The four services run as separate processes, which lets us make one of them fail without stopping the others."

## 1:40–3:10 | Scenario 1: normal successful transfer

```powershell
$normal = New-Transfer 150000
$ok = Send-Event $normal
$ok | Format-List transfer_id,state,correlation_id
"Sender: $(Get-Bal W-DEMO001)  Receiver: $(Get-Bal W-DEMO002)"
```

**Expect:** `COMPLETED`; sender 49850000; receiver 10150000.

**Say:** "We are sending 1,500 rupees. Compliance returned ALLOW. The service then debited the sender and credited a settlement clearing account. The rail confirmed settlement, after which clearing was debited and the receiver credited.

The sender decreased by exactly 150,000 paisa and the receiver increased by the same amount. Each journal must balance before it is accepted, and a database constraint prevents the same leg being posted twice for one transfer.

The result also carries a correlation ID and a transfer ID. The correlation ID is stored on the transfer and its journals. Notice the order of events: compliance comes before any money moves, and the receiver is never credited before the rail confirms. If screening had been unavailable, the transfer would have failed closed with no debit. If the amount had exceeded 400,000 rupees, it would have been placed on hold for a human decision."

## 3:10–5:20 | Scenario 2: client retry after timeout

**Part A: Gateway replay**

```powershell
$headers=@{"Idempotency-Key"="demo-$([guid]::NewGuid())";Authorization="Bearer synthetic"}
$body=@{sender_wallet_id="W-DEMO001";receiver_wallet_id="W-DEMO002";amount_minor=150000}|ConvertTo-Json
1..2 | ForEach-Object { $r=Invoke-WebRequest -UseBasicParsing -Method Post "$G/v1/transfers" -Headers $headers -ContentType application/json -Body $body; "$($r.StatusCode) $(($r.Content|ConvertFrom-Json).transfer_id) replayed=$($r.Headers['Idempotent-Replayed'])" }
```

**Expect:** two 201 responses, same transfer ID, second `replayed=true`.

**Say:** "At the edge, we send the same request twice with the same key. The transfer ID is identical and the second response is marked as replayed. This confirms duplicate suppression at the Gateway; because its downstream call is stubbed, this request does not change the ledger."

**Part B: lost response at the Transaction Service**

```powershell
Set-Rail TIMEOUT_NOT_SETTLED
$before = Get-Bal W-DEMO001
$retry = New-Transfer 200000
try { Send-Event $retry 1 } catch { $_.Exception.Message }
Start-Sleep 6
$second = Send-Event $retry
"Retry: $($second.status); outcome: $($second.snapshot.state)"
"Net change: $((Get-Bal W-DEMO001)-$before)"
Set-Rail SUCCESS
```

**Expect:** a client timeout message; `duplicate`; `REVERSED`; net change 0.

**Say while waiting:** "Now the rail is unresponsive and our client gives up after one second. The client does not know whether money moved. The server continues independently: it times out on the rail, inquires, finds no settlement, and compensates.

We wait for processing to finish, then resend the same event. The inbox recognises it and returns the recorded outcome. There is no second debit and the net change is zero. Our improvement backlog includes retries that arrive while the first request is still running, and rail outcomes that remain genuinely unknown."

## 5:20–6:50 | Scenario 3: partial failure and compensation

```powershell
Set-Rail REJECT
$before = Get-Bal W-DEMO001
$reversed = Send-Event (New-Transfer 300000)
"State: $($reversed.state)  Net change: $((Get-Bal W-DEMO001)-$before)"
$env:TID = $reversed.transfer_id
python -c "import sqlite3,os; [print(r) for r in sqlite3.connect('txn.db').execute('select from_state,to_state,reason from txn_state_history where transfer_id=? order by id',(os.environ['TID'],))]"
Set-Rail SUCCESS
```

**Expect:** `REVERSED`, net change 0, and four transitions ending `COMPENSATING → REVERSED`.

**Say:** "This is the dangerous partial failure: the debit has committed, and then the rail rejects settlement. We cannot roll back an external system, so we use a compensating transaction.

The state history shows screening, debit, compensation and reversal. The original debit remains in the ledger. A separate reversing journal refunds the sender, so the money is restored without erasing the evidence.

We chose this saga approach over two-phase commit because an external rail cannot be expected to take part in our database transaction, and we do not want to hold locks while waiting for it. The important distinction is that a rejection is a known answer. A timeout is not an answer at all. Our review found that the current code treats some unknown outcomes as failures, and we have recorded that as a critical release blocker instead of hiding it."

## 6:50–8:20 | Scenario 4: reconciliation outcome

```powershell
$breakTx = Send-Event (New-Transfer 100000)
Invoke-RestMethod -Method Post "$R/rail/admin/inject-break?transfer_id=$($breakTx.transfer_id)&kind=tamper_amount"
$date = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
python -m services.txn.recon --date $date
$breakTx.transfer_id
Get-Content "reports\recon_$date.csv"
```

**Expect:** `AMOUNT_MISMATCH` includes the displayed transfer ID. On a clean run, breaks = 1.

**Say:** "Finally, we create a valid transfer and deliberately alter the mock rail's record. Reconciliation compares the ledger with the rail for the UTC business date.

It finds an amount mismatch, writes JSON and CSV evidence, and opens an exception in the database. It does not silently adjust a balance. An operations analyst must investigate. In our target design, AI may help prioritise an exception or fraud alert, but it has no route to the ledger and cannot release or move money.

This control is deliberately independent of the transaction path. Even if the online logic contains a defect, comparing two separate records gives us another opportunity to detect it. Reconciliation is therefore a detective control, while idempotency and the ledger constraints are preventive controls."

## 8:20–9:00 | Close

**Say:** "We have shown one successful flow, a retry after client timeout, compensation after partial failure, and a detected reconciliation break. The state, ledger and evidence remain understandable in each case.

Our recommendation is Go for academic demonstration with synthetic data, and No-Go for live funds. Before that could change, we must connect the Gateway, secure internal commands, harden ambiguous settlement handling, and prove concurrency on PostgreSQL. Thank you."

## Recovery during recording

- **Unexpected state:** run `Set-Rail SUCCESS`, show the actual result, and restart the take.
- **Extra breaks:** restarting the in-memory rail loses records. Restart from a fresh seeded database.
- **Connection error:** confirm ports 8000, 8001, 8002 and 8004.
- Never edit timings or output to make a failed run appear successful.
