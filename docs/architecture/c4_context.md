# C4 Context Diagram

```mermaid
C4Context
  Person(customer, "Customer", "Sends wallet-to-wallet transfers")
  Person(ops, "Ops Analyst", "Investigates recon breaks")
  Person(compliance, "Compliance Officer", "Reviews fraud alerts")
  
  System(wallet, "SadaPay-inspired Wallet System", "Transfer system")
  
  System_Ext(rail, "Settlement Rail (mock)", "External settlement")
  
  Rel(customer, wallet, "Initiates transfer via API", "HTTPS/JSON")
  Rel(ops, wallet, "Resolves recon exceptions", "HTTPS")
  Rel(compliance, wallet, "Resolves fraud holds", "HTTPS")
  Rel(wallet, rail, "Settles via", "HTTPS/JSON")