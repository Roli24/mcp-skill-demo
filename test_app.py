"""Minimal tests for the demo API. Run: pytest"""

import os
import sqlite3

import pytest

import app as app_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(app_module, "DB_PATH", str(db_path))
    app_module.init_db()

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
        ("alice", "hashed-pw", 0),
    )
    conn.commit()
    conn.close()

    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_login_success(client):
    resp = client.post("/login", json={"username": "alice", "password_hash": "hashed-pw"})
    assert resp.status_code == 200
    assert resp.get_json()["username"] == "alice"


def test_login_bad_password(client):
    resp = client.post("/login", json={"username": "alice", "password_hash": "wrong"})
    assert resp.status_code == 401
