"""Tiny demo storefront API.

A deliberately small Flask app used to demo MCP + Skills in Claude Code:
  - GitHub MCP server lets Claude pull live PR/issue/CI context from GitHub.
  - The /code-review skill reviews a PR's diff for correctness/security issues.

Run: python app.py
"""

import sqlite3

from flask import Flask, g, jsonify, request

app = Flask(__name__)
DB_PATH = "demo.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
               id INTEGER PRIMARY KEY,
               username TEXT UNIQUE NOT NULL,
               password_hash TEXT NOT NULL,
               is_admin INTEGER NOT NULL DEFAULT 0
           )"""
    )
    conn.commit()
    conn.close()


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/login")
def login():
    """Authenticate a user. Uses a parameterized query, so it's safe
    against SQL injection.
    """
    username = request.json.get("username", "")
    password_hash = request.json.get("password_hash", "")

    db = get_db()
    row = db.execute(
        "SELECT id, username, is_admin FROM users "
        "WHERE username = ? AND password_hash = ?",
        (username, password_hash),
    ).fetchone()

    if row is None:
        return jsonify(error="invalid credentials"), 401

    return jsonify(id=row["id"], username=row["username"], is_admin=bool(row["is_admin"]))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
