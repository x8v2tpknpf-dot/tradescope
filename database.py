import sqlite3
import json
import os

DB_PATH = os.environ.get("DB_PATH", "tradescope.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                email       TEXT    UNIQUE NOT NULL,
                password    TEXT    NOT NULL,
                created_at  TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS analyses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                trades_json  TEXT    NOT NULL,
                stats_json   TEXT    NOT NULL,
                ai_report    TEXT    NOT NULL,
                issues_json  TEXT,
                created_at   TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)


def create_user(email: str, password_hash: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, password) VALUES (?, ?)",
            (email, password_hash)
        )
        return cur.lastrowid


def get_user_by_email(email: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None


def save_analysis(user_id: int, trades: list, stats: dict,
                  ai_report: str, issues: list) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO analyses
               (user_id, trades_json, stats_json, ai_report, issues_json)
               VALUES (?, ?, ?, ?, ?)""",
            (
                user_id,
                json.dumps(trades, ensure_ascii=False),
                json.dumps(stats, ensure_ascii=False),
                ai_report,
                json.dumps(issues, ensure_ascii=False),
            )
        )
        return cur.lastrowid


def get_last_analysis(user_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM analyses WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["trades_json"] = json.loads(d["trades_json"])
        d["stats_json"] = json.loads(d["stats_json"])
        d["issues_json"] = json.loads(d["issues_json"]) if d["issues_json"] else []
        return d


def get_all_analyses(user_id: int) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, created_at, stats_json, issues_json FROM analyses WHERE user_id = ? ORDER BY created_at ASC",
            (user_id,)
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["stats_json"] = json.loads(d["stats_json"])
            d["issues_json"] = json.loads(d["issues_json"]) if d["issues_json"] else []
            result.append(d)
        return result
