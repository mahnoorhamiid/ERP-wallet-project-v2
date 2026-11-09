import pytest
import sqlite3
from libs.common.outbox import init_outbox, enqueue, dispatch_once

@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    init_outbox(connection)
    yield connection
    connection.close()

def test_outbox_enqueue_and_dispatch(conn):
    # Enqueue an event
    enqueue(conn, "event-123", "http://txn:8001/events", {"test": "data"})
    conn.commit()
    
    # Run the dispatcher
    sent = dispatch_once(conn)
    assert sent == 1
    
    # Verify it is now marked as SENT
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM gw_outbox WHERE event_id='event-123'")
    status = cursor.fetchone()[0]
    assert status == "SENT"