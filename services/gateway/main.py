"""Gateway service — the front door for all customer requests."""
import os
import sqlite3
from fastapi import FastAPI

from libs.common.correlation import CorrelationIdMiddleware
from services.gateway.idempotency import init_db
from services.gateway.routers import transfers

app = FastAPI(title="Gateway", version="0.1")
app.add_middleware(CorrelationIdMiddleware)

# Database setup (sqlite3 for gateway idempotency)
DB_FILE = "gateway.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
init_db(conn)
app.state.db_conn = conn

# Include routers
app.include_router(transfers.router)

@app.get("/health")
def health():
    return {"status": "ok"}