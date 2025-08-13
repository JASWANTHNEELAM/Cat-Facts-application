from flask import Flask, jsonify, render_template, request
import requests
import sqlite3
from pathlib import Path

app = Flask(__name__)

CATFACT_URL = "https://catfact.ninja/fact"
DB_FILE = "facts.db"

# ---------------------------
# DB helpers
# ---------------------------
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    Path(DB_FILE).touch(exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT (datetime('now', '+5 hours', '30 minutes'))
            )
        """)
init_db()

def save_fact_to_db(fact_text):
    with get_db() as conn:
        conn.execute("INSERT INTO facts (fact) VALUES (?)", (fact_text,))

def fetch_facts(search: str | None = None):
    query = "SELECT fact, created_at FROM facts"
    params = ()
    if search:
        query += " WHERE fact LIKE ?"
        params = (f"%{search}%",)
    query += " ORDER BY id DESC"
    with get_db() as conn:
        return conn.execute(query, params).fetchall()

# ---------------------------
# API route (backend → third-party)
# ---------------------------
@app.get("/fact")
def get_fact():
    try:
        r = requests.get(CATFACT_URL, timeout=5)
        r.raise_for_status()
        data = r.json()
        fact = data.get("fact", "No fact available right now.")
        save_fact_to_db(fact)
        return jsonify({"fact": fact})
    except requests.exceptions.RequestException:
        return jsonify({"error": "Unable to fetch fact at the moment."}), 503
    except ValueError:
        return jsonify({"error": "Received invalid JSON from upstream."}), 502

# ---------------------------
# Pages
# ---------------------------
@app.get("/")
def index():
    return render_template("index.html")

@app.get("/history")
def history():
    q = request.args.get("q", "").strip() or None
    rows = fetch_facts(q)
    return render_template("history.html", facts=rows, q=(q or ""))

if __name__ == "__main__":
    app.run(debug=True)
