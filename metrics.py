import sqlite3
import time
from database import get_connection, save_metrics

def get_realtime_metrics():
    """
    Computes real-time metrics directly from the current request logs and server tables.
    Returns a dictionary of aggregated metrics.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get overall counts
        cursor.execute("SELECT COUNT(*) FROM request_logs")
        total_requests = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM request_logs WHERE status_code >= 200 AND status_code < 400")
        successful_requests = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM request_logs WHERE status_code >= 400 OR status_code IS NULL")
        failed_requests = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(response_time_ms) FROM request_logs WHERE response_time_ms IS NOT NULL")
        avg_response_time = cursor.fetchone()[0] or 0.0

        # Get active connections and count healthy/unhealthy servers
        cursor.execute("SELECT SUM(active_connections) FROM servers")
        active_connections = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM servers WHERE status = 'healthy'")
        healthy_servers = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM servers WHERE status = 'unhealthy'")
        unhealthy_servers = cursor.fetchone()[0]

        # Calculate traffic distribution
        cursor.execute("""
            SELECT s.name, COUNT(r.id) as count 
            FROM servers s
            LEFT JOIN request_logs r ON s.id = r.server_id
            GROUP BY s.id
        """)
        distribution = {row['name']: row['count'] for row in cursor.fetchall()}

        # Average response time per server
        cursor.execute("""
            SELECT s.name, AVG(r.response_time_ms) as avg_time 
            FROM servers s
            LEFT JOIN request_logs r ON s.id = r.server_id
            WHERE r.response_time_ms IS NOT NULL
            GROUP BY s.id
        """)
        latency_distribution = {row['name']: round(row['avg_time'], 2) if row['avg_time'] else 0.0 for row in cursor.fetchall()}

        # Server utilization (proxied by current active connections / capacity)
        cursor.execute("SELECT name, active_connections, weight FROM servers")
        utilization = []
        for row in cursor.fetchall():
            weight = row['weight'] or 1
            active = row['active_connections'] or 0
            # weight represents maximum concurrent connection capability in weighted logic,
            # so utilization = (active / weight) * 100
            util_pct = min(100.0, round((active / float(weight)) * 100, 1))
            utilization.append({
                "name": row['name'],
                "active": active,
                "weight": weight,
                "utilization": util_pct
            })

        metrics_data = {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "avg_response_time": round(avg_response_time, 2),
            "active_connections": active_connections,
            "healthy_servers": healthy_servers,
            "unhealthy_servers": unhealthy_servers,
            "distribution": distribution,
            "latency_distribution": latency_distribution,
            "utilization": utilization
        }
        
        return metrics_data

    except sqlite3.Error as e:
        print(f"[!] SQLite Error in metrics collection: {e}")
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "active_connections": 0,
            "healthy_servers": 0,
            "unhealthy_servers": 0,
            "distribution": {},
            "latency_distribution": {},
            "utilization": []
        }
    finally:
        conn.close()

def record_metrics_snapshot():
    """
    Saves a snapshot of current metrics to the metrics table for historical analytics.
    """
    stats = get_realtime_metrics()
    save_metrics(
        stats["total_requests"],
        stats["successful_requests"],
        stats["failed_requests"],
        stats["avg_response_time"],
        stats["active_connections"]
    )

def get_metrics_history(limit=20):
    """
    Retrieves historical metrics logs for line chart displays.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM metrics ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    # Reverse so timeline flows left-to-right
    rows.reverse()
    return rows
