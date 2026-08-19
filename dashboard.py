import time
import uuid
import threading
import requests
from flask import Blueprint, render_template, jsonify, request

import database
from load_balancer import LoadBalancer
import server_manager
import metrics

# Create Flask Blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# Core Balancer instance
balancer = LoadBalancer()

# In-memory states for the load balancer dashboard
CURRENT_ALGORITHM = "least_connections"
TRAFFIC_GENERATOR_RUNNING = False
TRAFFIC_GENERATOR_THREAD = None
TRAFFIC_GENERATOR_RATE = 2  # requests per second
LOCK = threading.Lock()

# Define HTML page view
@dashboard_bp.route('/')
def index():
    return render_template('index.html')

# API: GET /servers
@dashboard_bp.route('/servers', methods=['GET'])
def get_servers():
    servers = database.get_servers()
    # Merge current simulation state from server_manager
    for s in servers:
        sim_state = server_manager.get_server_simulation_state(s['url'])
        s['simulated_status'] = sim_state['status']
        s['simulated_delay'] = sim_state['delay']
    return jsonify(servers)

# API: GET /metrics
@dashboard_bp.route('/metrics', methods=['GET'])
def get_metrics():
    stats = metrics.get_realtime_metrics()
    return jsonify(stats)

# API: GET /health
@dashboard_bp.route('/health', methods=['GET'])
def get_health():
    return jsonify({
        "status": "online",
        "load_balancer_health": "healthy",
        "current_algorithm": CURRENT_ALGORITHM,
        "active_connections": database.get_servers()
    })

# API: POST /request (Routes traffic through the load balancer)
@dashboard_bp.route('/request', methods=['POST'])
def process_request():
    global CURRENT_ALGORITHM
    
    # Generate unique request ID
    req_id = str(uuid.uuid4())
    
    # Get request body or generate dynamic content
    req_body = request.get_json(silent=True) or {}
    payload = req_body.get('payload', 'Direct client request')
    
    # 1. Fetch current list of servers
    servers = database.get_servers()
    
    # 2. Select target server based on active algorithm
    selected_server = balancer.select_server(servers, CURRENT_ALGORITHM)
    
    if not selected_server:
        # No healthy servers available
        database.log_request(req_id, None, CURRENT_ALGORITHM, 0.0, 503)
        return jsonify({
            "status": "error",
            "request_id": req_id,
            "error": "Service Unavailable: No healthy backend servers available in routing pool.",
            "status_code": 503
        }), 503

    server_id = selected_server['id']
    server_url = selected_server['url']
    server_name = selected_server['name']

    # 3. Increment active connection count (Least Connections tracking)
    database.update_server_connections(server_id, 1)

    start_time = time.time()
    response_code = None
    response_data = None
    
    try:
        # Forward request to mock backend HTTP server (2 second timeout)
        response = requests.post(f"{server_url}/request", data=payload, timeout=2.0)
        latency = (time.time() - start_time) * 1000  # in ms
        response_code = response.status_code
        response_data = response.json()
    except requests.exceptions.RequestException:
        # Fallback to in-process simulation state if HTTP socket connection is unreachable (e.g., Vercel)
        response_code, response_data = server_manager.simulate_mock_request(server_url, payload)
        latency = (time.time() - start_time) * 1000
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        response_code = 500
        response_data = {"error": f"Internal routing error: {str(e)}"}

    # 4. Decrement active connection count
    database.update_server_connections(server_id, -1)

    # 5. Log the request transaction in database
    database.log_request(req_id, server_id, CURRENT_ALGORITHM, latency, response_code)

    # 6. Save a metrics snapshot to database for historical analytics
    metrics.record_metrics_snapshot()

    return jsonify({
        "status": "success" if response_code == 200 else "failed",
        "request_id": req_id,
        "algorithm_used": CURRENT_ALGORITHM,
        "routed_to": {
            "id": server_id,
            "name": server_name,
            "url": server_url
        },
        "response_time_ms": round(latency, 2),
        "status_code": response_code,
        "backend_response": response_data
    }), response_code

# API: POST /simulate-traffic (Start/Stop background load generator)
@dashboard_bp.route('/simulate-traffic', methods=['POST'])
def simulate_traffic():
    global TRAFFIC_GENERATOR_RUNNING, TRAFFIC_GENERATOR_THREAD, TRAFFIC_GENERATOR_RATE
    
    req_body = request.get_json(silent=True) or {}
    active = req_body.get('active', True)
    rate = req_body.get('rate', 2) # Requests per second
    
    with LOCK:
        if active:
            TRAFFIC_GENERATOR_RATE = max(1, min(10, rate)) # Cap rate between 1 and 10 rps
            if not TRAFFIC_GENERATOR_RUNNING:
                TRAFFIC_GENERATOR_RUNNING = True
                TRAFFIC_GENERATOR_THREAD = threading.Thread(target=traffic_generator_worker, daemon=True)
                TRAFFIC_GENERATOR_THREAD.start()
                message = f"Simulated traffic active at {TRAFFIC_GENERATOR_RATE} requests/sec."
            else:
                message = f"Updated simulation traffic rate to {TRAFFIC_GENERATOR_RATE} requests/sec."
        else:
            TRAFFIC_GENERATOR_RUNNING = False
            TRAFFIC_GENERATOR_THREAD = None
            message = "Simulated traffic stopped."
            
    return jsonify({
        "status": "success",
        "traffic_sim_active": TRAFFIC_GENERATOR_RUNNING,
        "rate": TRAFFIC_GENERATOR_RATE,
        "message": message
    })

def traffic_generator_worker():
    """
    Background worker thread generating request traffic to the load balancer endpoint.
    """
    global TRAFFIC_GENERATOR_RUNNING, TRAFFIC_GENERATOR_RATE
    print("[*] Traffic Generator Thread Active")
    
    while TRAFFIC_GENERATOR_RUNNING:
        try:
            # Self-invoke the POST request route locally on Flask's default port 8080
            requests.post(
                "http://127.0.0.1:8080/request", 
                json={"payload": f"Simulated stress load user request"}, 
                timeout=3.0
            )
        except Exception:
            pass # Suppress exceptions from startup delays or transient restarts
        
        # Interval based on rate
        time.sleep(1.0 / TRAFFIC_GENERATOR_RATE)
        
    print("[*] Traffic Generator Thread Stopped")

# API: POST /simulate-failure (Mark server offline in simulator)
@dashboard_bp.route('/simulate-failure', methods=['POST'])
def simulate_failure():
    req_body = request.get_json(silent=True) or {}
    server_id = req_body.get('server_id')
    
    if not server_id:
        return jsonify({"status": "error", "message": "server_id is required"}), 400
        
    servers = database.get_servers()
    target = next((s for s in servers if s['id'] == int(server_id)), None)
    
    if not target:
        return jsonify({"status": "error", "message": "Server not found"}), 404
        
    # Mark offline in simulator
    server_manager.set_server_simulation_state(target['url'], status='offline')
    # Instantly trigger database update so the change reflects on dashboard immediately
    database.update_server_status(target['id'], 'unhealthy')
    # Ensure connections are reset to 0
    database.update_server_connections(target['id'], -9999) 
    
    return jsonify({
        "status": "success",
        "server_id": server_id,
        "message": f"Server {target['name']} set to offline. Health checker will trigger failover."
    })

# API: POST /recover-server (Mark server back online in simulator)
@dashboard_bp.route('/recover-server', methods=['POST'])
def recover_server():
    req_body = request.get_json(silent=True) or {}
    server_id = req_body.get('server_id')
    
    if not server_id:
        return jsonify({"status": "error", "message": "server_id is required"}), 400
        
    servers = database.get_servers()
    target = next((s for s in servers if s['id'] == int(server_id)), None)
    
    if not target:
        return jsonify({"status": "error", "message": "Server not found"}), 404
        
    # Mark online in simulator
    server_manager.set_server_simulation_state(target['url'], status='online')
    # Trigger database update so dashboard reacts instantly
    database.update_server_status(target['id'], 'healthy')
    
    return jsonify({
        "status": "success",
        "server_id": server_id,
        "message": f"Server {target['name']} set to online. Health checker will recover connection routing."
    })

# API: POST /set-algorithm (Change active load balancer algorithm)
@dashboard_bp.route('/set-algorithm', methods=['POST'])
def set_algorithm():
    global CURRENT_ALGORITHM
    req_body = request.get_json(silent=True) or {}
    algo = req_body.get('algorithm')
    
    valid_algos = ["round_robin", "weighted_round_robin", "least_connections"]
    if not isinstance(algo, str) or algo not in valid_algos:
        return jsonify({"status": "error", "message": f"Invalid algorithm. Must be one of {valid_algos}"}), 400
        
    CURRENT_ALGORITHM = algo
    return jsonify({
        "status": "success",
        "algorithm": CURRENT_ALGORITHM,
        "message": f"Load balancer routing changed to: {algo.replace('_', ' ').title()}"
    })

# API: POST /update-weight (Configure weighted round robin weightings)
@dashboard_bp.route('/update-weight', methods=['POST'])
def update_weight():
    req_body = request.get_json(silent=True) or {}
    server_id = req_body.get('server_id')
    weight = req_body.get('weight')
    
    if not server_id or weight is None:
        return jsonify({"status": "error", "message": "server_id and weight are required"}), 400
        
    try:
        weight_val = max(1, int(weight))
    except ValueError:
        return jsonify({"status": "error", "message": "weight must be an integer"}), 400
        
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE servers SET weight = ? WHERE id = ?", (weight_val, server_id))
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "success",
        "server_id": server_id,
        "weight": weight_val,
        "message": "Server weight updated successfully."
    })

# API: POST /update-delay (Configure simulated server latency)
@dashboard_bp.route('/update-delay', methods=['POST'])
def update_delay():
    req_body = request.get_json(silent=True) or {}
    url = req_body.get('url')
    delay = req_body.get('delay')
    
    if not url or delay is None:
        return jsonify({"status": "error", "message": "url and delay are required"}), 400
        
    try:
        delay_val = max(0.0, float(delay))
    except ValueError:
        return jsonify({"status": "error", "message": "delay must be a float or integer"}), 400
        
    server_manager.set_server_simulation_state(url, delay=delay_val)
    
    return jsonify({
        "status": "success",
        "url": url,
        "delay": delay_val,
        "message": "Server simulated latency updated successfully."
    })

# API: GET /dashboard-data (Consolidated data for React/Vanilla JS frontend polling)
@dashboard_bp.route('/dashboard-data', methods=['GET'])
def dashboard_data():
    servers = database.get_servers()
    # Inject simulation parameters
    for s in servers:
        sim_state = server_manager.get_server_simulation_state(s['url'])
        s['simulated_status'] = sim_state['status']
        s['simulated_delay'] = sim_state['delay']

    recent_logs = database.get_recent_logs(limit=15)
    stats = metrics.get_realtime_metrics()
    history = metrics.get_metrics_history(limit=15)
    
    return jsonify({
        "servers": servers,
        "metrics": stats,
        "logs": recent_logs,
        "history": history,
        "current_algorithm": CURRENT_ALGORITHM,
        "traffic_sim_active": TRAFFIC_GENERATOR_RUNNING,
        "traffic_sim_rate": TRAFFIC_GENERATOR_RATE
    })
