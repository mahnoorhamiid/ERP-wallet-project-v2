"""Gateway idempotency store (using built-in sqlite3 to avoid Windows blocks)."""
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from enum import Enum

from libs.common.clock import now

STALE_AFTER_S = int(os.getenv("IDEMPOTENCY_STALE_AFTER_S", "30"))
EXPIRY_HOURS = 24

class IdemState(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

def init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gw_idempotency (
            client_id TEXT,
            idempotency_key TEXT,
            request_hash TEXT,
            state TEXT,
            transfer_id TEXT,
            event_id TEXT,
            response_code INTEGER,
            response_body TEXT,
            created_at TEXT,
            expires_at TEXT,
            PRIMARY KEY (client_id, idempotency_key)
        )
    """)
    conn.commit()

def hash_request(body: dict) -> str:
    """SHA-256 of canonical JSON."""
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()

def begin(conn: sqlite3.Connection, client_id: str, key: str, request_hash: str) -> tuple[dict, bool]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gw_idempotency WHERE client_id=? AND idempotency_key=?", (client_id, key))
    row = cursor.fetchone()
    
    if row:
        # Existing row found
        return dict(zip([d[0] for d in cursor.description], row)), False
    
    # New row
    now_time = now()
    expires = now_time + timedelta(hours=EXPIRY_HOURS)
    cursor.execute(
        "INSERT INTO gw_idempotency (client_id, idempotency_key, request_hash, state, transfer_id, event_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (client_id, key, request_hash, IdemState.IN_PROGRESS.value, "", "", now_time.isoformat(), expires.isoformat())
    )
    conn.commit()
    
    # Return the new row directly instead of re-querying
    return {
        "client_id": client_id,
        "idempotency_key": key,
        "request_hash": request_hash,
        "state": IdemState.IN_PROGRESS.value,
        "transfer_id": "",
        "event_id": "",
        "created_at": now_time.isoformat(),
        "expires_at": expires.isoformat()
    }, True

def complete(conn: sqlite3.Connection, client_id: str, key: str, response_code: int, response_body: dict):
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE gw_idempotency SET state=?, response_code=?, response_body=? WHERE client_id=? AND idempotency_key=?",
        (IdemState.COMPLETED.value, response_code, json.dumps(response_body), client_id, key)
    )
    conn.commit()

def is_stale(row: dict) -> bool:
    created = datetime.fromisoformat(row["created_at"])
    age = (now() - created).total_seconds()
    return age >= STALE_AFTER_S