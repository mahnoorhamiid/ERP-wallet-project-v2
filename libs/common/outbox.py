"""Outbox pattern for reliable event dispatching."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from libs.common.clock import now

def init_outbox(conn: sqlite3.Connection, table_name: str = "gw_outbox"):
    """Create the outbox table if it doesn't exist."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            event_id TEXT PRIMARY KEY,
            target_url TEXT,
            payload_json TEXT,
            status TEXT,
            attempts INTEGER,
            next_attempt_at TEXT,
            created_at TEXT
        )
    """)
    conn.commit()

def enqueue(conn: sqlite3.Connection, event_id: str, target_url: str, payload: dict, table_name: str = "gw_outbox"):
    """Insert an event into the outbox inside the current DB transaction."""
    payload_json = json.dumps(payload)
    now_time = now().isoformat()
    
    conn.execute(f"""
        INSERT INTO {table_name} (event_id, target_url, payload_json, status, attempts, next_attempt_at, created_at)
        VALUES (?, ?, ?, 'PENDING', 0, ?, ?)
    """, (event_id, target_url, payload_json, now_time, now_time))
    # We do NOT commit here. We let the caller commit so the state change and event commit together.

def dispatch_once(conn: sqlite3.Connection, table_name: str = "gw_outbox"):
    """Find due PENDING events, send them, and update their status."""
    cursor = conn.cursor()
    current_time = now().isoformat()
    
    # Find events that are pending and due
    cursor.execute(f"""
        SELECT event_id, target_url, payload_json, attempts 
        FROM {table_name} 
        WHERE status = 'PENDING' AND next_attempt_at <= ?
    """, (current_time,))
    
    rows = cursor.fetchall()
    if not rows:
        return 0
        
    sent_count = 0
    for row in rows:
        event_id, target_url, payload_json, attempts = row
        
        # ---------------------------------------------------------
        # IN A REAL APP: Here we would use httpx to POST to target_url.
        # For this local test, we will just print it and assume success.
        print(f"Dispatching {event_id} to {target_url}...")
        # ---------------------------------------------------------
        
        # Mark as SENT
        cursor.execute(f"""
            UPDATE {table_name} 
            SET status = 'SENT', attempts = attempts + 1 
            WHERE event_id = ?
        """, (event_id,))
        sent_count += 1
        
    conn.commit()
    return sent_count