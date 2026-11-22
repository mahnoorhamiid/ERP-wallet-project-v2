import os
import uuid
import sqlite3
import threading
from fastapi import FastAPI, Header
from pydantic import BaseModel, Field
from typing import List, Optional
from libs.common.clock import now
from libs.common.correlation import get_correlation_id

app = FastAPI(title="Bounded AI Triage Service")
db_lock = threading.Lock()
DB_PATH = os.getenv("AI_DB_PATH", ":memory:" if "pytest" in os.environ.get("_", "") else "ai_triage.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_recommendations (
            recommendation_id TEXT PRIMARY KEY,
            alert_id TEXT UNIQUE,
            correlation_id TEXT,
            priority TEXT,
            disposition TEXT,
            confidence REAL,
            abstained BOOLEAN,
            model_version TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup_event():
    init_db()

class FraudAlert(BaseModel):
    alert_id: str
    transfer_id: str
    amount_minor: int
    risk_signals: List[str]
    correlation_id: str

def calculate_confidence(alert: FraudAlert) -> float:
    score = 0.5 
    if "AML_ALERT" in alert.risk_signals:
        score += 0.4 
    if alert.amount_minor > 40000000: 
        score += 0.1 
    return min(score, 1.0) 

@app.get("/health")
def health():
    return {"status": "healthy", "service": "ai-triage"}

@app.post("/internal/v1/triage")
def triage_alert(alert: FraudAlert, x_correlation_id: Optional[str] = Header(None)):
    cid = x_correlation_id or get_correlation_id() or str(uuid.uuid4())
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_recommendations WHERE alert_id = ?", (alert.alert_id,))
    row = cursor.fetchone()
    
    if row:
        conn.close()
        return {
            "recommendation_id": row[0], "alert_id": row[1], "correlation_id": row[2],
            "priority": row[3], "disposition": row[4], "confidence": row[5],
            "abstained": bool(row[6]), "model_version": row[7], "created_at": row[8]
        }


    confidence = calculate_confidence(alert)
    threshold = float(os.getenv("AI_ABSTAIN_THRESHOLD", "0.70"))
    model_ver = os.getenv("AI_MODEL_VERSION", "v1.0-deterministic")

    if confidence < threshold:
        abstained = True
        priority = None
        disposition = "ABSTAIN"
    else:
        abstained = False
        if "AML_ALERT" in alert.risk_signals:
            priority = "HIGH"
            disposition = "REVIEW_REJECT"
        else:
            priority = "MEDIUM"
            disposition = "REVIEW_RELEASE"

    rec_id = str(uuid.uuid4())
    created_at = now().isoformat()
    
    cursor.execute("""
        INSERT INTO ai_recommendations 
        (recommendation_id, alert_id, correlation_id, priority, disposition, confidence, abstained, model_version, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (rec_id, alert.alert_id, cid, priority, disposition, confidence, abstained, model_ver, created_at))
    conn.commit()
    conn.close()

    return {
        "recommendation_id": rec_id, "alert_id": alert.alert_id, "correlation_id": cid,
        "priority": priority, "disposition": disposition, "confidence": confidence,
        "abstained": abstained, "model_version": model_ver, "created_at": created_at
    }