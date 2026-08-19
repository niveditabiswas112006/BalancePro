import sqlite3
import os
from datetime import datetime

DB_FILE = "balancepro.db"

def get_db_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if os.environ.get('VERCEL') == '1' or not os.access(base_dir, os.W_OK):
        import tempfile
        return os.path.join(tempfile.gettempdir(), DB_FILE)
    return os.path.join(base_dir, DB_FILE)

def get_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create Servers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        url TEXT NOT NULL UNIQUE,
        weight INTEGER DEFAULT 1,
        status TEXT DEFAULT 'healthy',
        active_connections INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create Request Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS request_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT NOT NULL,
        server_id INTEGER,
        algorithm_used TEXT NOT NULL,
        response_time_ms REAL,
        status_code INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE SET NULL
    )
    """)

    # Create Metrics Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_requests INTEGER DEFAULT 0,
        successful_requests INTEGER DEFAULT 0,
        failed_requests INTEGER DEFAULT 0,
        avg_response_time REAL DEFAULT 0.0,
        active_connections INTEGER DEFAULT 0
    )
    """)

    # Create Health Status History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS health_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        server_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        response_time REAL,
        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
    )
    """)

    # Insert default servers if the table is empty
    cursor.execute("SELECT COUNT(*) FROM servers")
    if cursor.fetchone()[0] == 0:
        default_servers = [
            ("Server-1 (Alpha)", "http://127.0.0.1:5001", 3),
            ("Server-2 (Beta)", "http://127.0.0.1:5002", 5),
            ("Server-3 (Gamma)", "http://127.0.0.1:5003", 2),
            ("Server-4 (Delta)", "http://127.0.0.1:5004", 1)
        ]
        cursor.executemany(
            "INSERT INTO servers (name, url, weight, status) VALUES (?, ?, ?, 'healthy')",
            default_servers
        )
        conn.commit()

    conn.close()

def get_servers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM servers")
    servers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return servers

def update_server_status(server_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE servers SET status = ? WHERE id = ?", (status, server_id))
    conn.commit()
    conn.close()

def update_server_connections(server_id, delta):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE servers SET active_connections = MAX(0, active_connections + ?) WHERE id = ?",
        (delta, server_id)
    )
    conn.commit()
    conn.close()

def reset_all_connections():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE servers SET active_connections = 0")
    conn.commit()
    conn.close()

def log_request(request_id, server_id, algorithm, response_time, status_code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO request_logs (request_id, server_id, algorithm_used, response_time_ms, status_code)
        VALUES (?, ?, ?, ?, ?)
        """,
        (request_id, server_id, algorithm, response_time, status_code)
    )
    conn.commit()
    conn.close()

def log_health_check(server_id, status, response_time):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO health_status (server_id, status, response_time)
        VALUES (?, ?, ?)
        """,
        (server_id, status, response_time)
    )
    conn.commit()
    conn.close()

def save_metrics(total_req, success_req, failed_req, avg_resp, active_conn):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO metrics (total_requests, successful_requests, failed_requests, avg_response_time, active_connections)
        VALUES (?, ?, ?, ?, ?)
        """,
        (total_req, success_req, failed_req, avg_resp, active_conn)
    )
    conn.commit()
    conn.close()

def get_recent_logs(limit=25):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.*, s.name as server_name 
        FROM request_logs r 
        LEFT JOIN servers s ON r.server_id = s.id 
        ORDER BY r.timestamp DESC 
        LIMIT ?
        """,
        (limit,)
    )
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs
