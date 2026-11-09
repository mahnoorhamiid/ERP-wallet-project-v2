"""Idempotency algorithm tests using sqlite3."""
import pytest
import sqlite3
from services.gateway.idempotency import (
    init_db, begin, complete, hash_request, IdemState
)

@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    init_db(connection)
    yield connection
    connection.close()

def test_first_request_is_new(conn):
    row, is_new = begin(conn, "alice", "key-12345678", hash_request({"a": 1}))
    assert is_new is True
    assert row["state"] == IdemState.IN_PROGRESS.value

def test_second_request_same_key_same_hash_is_not_new(conn):
    row1, is_new1 = begin(conn, "alice", "key-12345678", hash_request({"a": 1}))
    row2, is_new2 = begin(conn, "alice", "key-12345678", hash_request({"a": 1}))
    assert is_new1 is True
    assert is_new2 is False
    assert row1["idempotency_key"] == row2["idempotency_key"]

def test_hash_is_deterministic_regardless_of_key_order():
    h1 = hash_request({"a": 1, "b": 2})
    h2 = hash_request({"b": 2, "a": 1})
    assert h1 == h2