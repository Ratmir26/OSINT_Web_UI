import sqlite3
from datetime import datetime, timedelta


def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            search_type TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            results_summary TEXT
        );
        CREATE TABLE IF NOT EXISTS monitored_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL UNIQUE,
            interval_hours INTEGER DEFAULT 24,
            last_run DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS search_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id INTEGER,
            data_json TEXT,
            file_path TEXT,
            FOREIGN KEY (search_id) REFERENCES searches(id)
        );
    """)
    conn.commit()
    conn.close()


def add_search(db_path: str, query: str, search_type: str, results_summary: str = "") -> int:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO searches (query, search_type, results_summary) VALUES (?, ?, ?)",
        (query, search_type, results_summary)
    )
    conn.commit()
    search_id = cursor.lastrowid
    conn.close()
    return search_id


def get_history(db_path: str, limit: int = 20) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, query, search_type, timestamp, results_summary FROM searches ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def add_monitored(db_path: str, query: str, interval_hours: int = 24) -> bool:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO monitored_queries (query, interval_hours) VALUES (?, ?)",
            (query, interval_hours)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def remove_monitored(db_path: str, query: str) -> bool:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM monitored_queries WHERE query = ?", (query,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_monitored(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, query, interval_hours, last_run, created_at FROM monitored_queries"
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def check_due_monitored(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT query, interval_hours, last_run FROM monitored_queries"
    )
    due = []
    now = datetime.now()
    for row in cursor.fetchall():
        query, interval_hours, last_run_str = row
        if last_run_str is None:
            due.append(query)
        else:
            last_run = datetime.fromisoformat(last_run_str)
            if now >= last_run + timedelta(hours=interval_hours):
                due.append(query)
    conn.close()
    return due


def update_last_run(db_path: str, query: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE monitored_queries SET last_run = ? WHERE query = ?",
        (datetime.now().isoformat(), query)
    )
    conn.commit()
    conn.close()
