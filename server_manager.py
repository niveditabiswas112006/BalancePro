import http.server
import socketserver
import threading
import time
import json
import urllib.parse

# Global state to track simulation properties of the servers
# Format: { "http://127.0.0.1:5001": { "status": "online", "delay": 0.05 } }
SERVER_STATES = {}
LOCK = threading.Lock()

class MockServerHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress request logging in console to keep terminal clean
        pass

    def _get_server_config(self):
        # Construct URL based on this server's port
        host, port = self.server.server_address
        url = f"http://{host}:{port}"
        with LOCK:
            if url not in SERVER_STATES:
                SERVER_STATES[url] = {"status": "online", "delay": 0.0, "failure_rate": 0.0}
            return SERVER_STATES[url].copy()

    def do_GET(self):
        config = self._get_server_config()
        
        # Simulate failure
        if config["status"] == "offline":
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Service Unavailable (Simulated Failure)"}).encode())
            return

        # Simulate response delay
        if config["delay"] > 0:
            time.sleep(config["delay"])

        # Health Check Endpoint
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy", "message": "Server is running fine!"}).encode())
            return

        # Default GET Handler
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "message": "GET request processed successfully",
            "server": f"http://{self.server.server_address[0]}:{self.server.server_address[1]}"
        }).encode())

    def do_POST(self):
        config = self._get_server_config()

        # Simulate failure
        if config["status"] == "offline":
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Service Unavailable (Simulated Failure)"}).encode())
            return

        # Simulate response delay
        if config["delay"] > 0:
            time.sleep(config["delay"])

        # Read POST body
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ""

        # Default POST Handler
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        host, port = self.server.server_address
        response_data = {
            "status": "success",
            "server_port": port,
            "received_data": post_data,
            "processed_by": f"Server on Port {port}"
        }
        self.wfile.write(json.dumps(response_data).encode())

class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    # Enable socket reuse to avoid "Address already in use" on fast restarts
    allow_reuse_address = True

class MockServerThread(threading.Thread):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.daemon = True
        self.server = None

    def run(self):
        try:
            self.server = ThreadingHTTPServer((self.host, self.port), MockServerHandler)
            print(f"[*] Starting Mock Server on {self.host}:{self.port}")
            self.server.serve_forever()
        except Exception as e:
            print(f"[!] Error starting Mock Server on port {self.port}: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print(f"[*] Stopped Mock Server on port {self.port}")

# Store running server threads
_running_servers = {}

def start_all_mock_servers(servers):
    """
    Spins up mock servers in background threads if they aren't already running.
    servers: List of server dictionaries from database.
    """
    for server in servers:
        url = server['url']
        # Parse host and port from URL (e.g. http://127.0.0.1:5001)
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname or '127.0.0.1'
        port = parsed.port

        if not port:
            continue

        # Set default online state in simulation config
        with LOCK:
            if url not in SERVER_STATES:
                # Add default weight-based base delay to make servers behave differently:
                # Server 1 delay: 0.05s, Server 2 delay: 0.08s, Server 3 delay: 0.12s, Server 4 delay: 0.20s
                # This naturally demonstrates the Least Connections algorithm favoring faster servers!
                base_delay = 0.02 * (port - 5000) 
                SERVER_STATES[url] = {"status": "online", "delay": base_delay}

        if url not in _running_servers:
            thread = MockServerThread(host, port)
            thread.start()
            _running_servers[url] = thread
            # Give a small buffer to let socket bind
            time.sleep(0.1)

def stop_all_mock_servers():
    """
    Stops all running server threads.
    """
    for url, thread in list(_running_servers.items()):
        thread.stop()
        del _running_servers[url]

def set_server_simulation_state(url, status=None, delay=None):
    """
    Updates simulation behavior for a specific mock server URL.
    """
    with LOCK:
        if url not in SERVER_STATES:
            SERVER_STATES[url] = {"status": "online", "delay": 0.0}
        
        if status is not None:
            SERVER_STATES[url]["status"] = status
        if delay is not None:
            SERVER_STATES[url]["delay"] = float(delay)

def get_server_simulation_state(url):
    with LOCK:
        return SERVER_STATES.get(url, {"status": "online", "delay": 0.0}).copy()

def simulate_mock_request(url, payload=None):
    parsed = urllib.parse.urlparse(url)
    port = parsed.port or 5001
    config = get_server_simulation_state(url)
    if config.get("status") == "offline":
        return 503, {"error": "Service Unavailable (Simulated Failure)"}
    delay = config.get("delay", 0.0)
    if delay > 0:
        time.sleep(delay)
    return 200, {
        "status": "success",
        "server_port": port,
        "received_data": payload or "",
        "processed_by": f"Server on Port {port}"
    }

