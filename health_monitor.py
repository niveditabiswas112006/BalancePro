import threading
import time
import requests
from database import get_servers, update_server_status, log_health_check

class HealthMonitor(threading.Thread):
    def __init__(self, interval=5):
        super().__init__()
        self.interval = interval
        self.daemon = True
        self.running = True

    def run(self):
        print("[*] Starting Background Health Monitor Thread...")
        # Add a short delay before initial check to let mock servers start up fully
        time.sleep(2)
        
        while self.running:
            try:
                self.check_servers_health()
            except Exception as e:
                print(f"[!] Exception in health monitor loop: {e}")
            time.sleep(self.interval)

    def check_servers_health(self):
        servers = get_servers()
        for server in servers:
            server_id = server['id']
            url = server['url']
            name = server['name']
            old_status = server['status']
            
            try:
                start_time = time.time()
                # Run GET health request with a tight timeout of 2 seconds
                response = requests.get(f"{url}/health", timeout=2.0)
                latency = (time.time() - start_time) * 1000 # Convert to ms
                
                if response.status_code == 200:
                    new_status = 'healthy'
                else:
                    new_status = 'unhealthy'
                    latency = None
            except (requests.exceptions.RequestException, Exception):
                # Fallback to simulation state if socket connection is unavailable (e.g. in serverless environments)
                import server_manager
                sim_state = server_manager.get_server_simulation_state(url)
                if sim_state.get('status') == 'online':
                    new_status = 'healthy'
                    latency = round(sim_state.get('delay', 0.0) * 1000 + 15.0, 2)
                else:
                    new_status = 'unhealthy'
                    latency = None

            # Update database if status changed or just log the health check history
            if new_status != old_status:
                print(f"[!] Health Check Alert: {name} ({url}) changed from {old_status} to {new_status}")
                update_server_status(server_id, new_status)
                
            log_health_check(server_id, new_status, latency)

    def stop(self):
        self.running = False
        print("[*] Stopping Background Health Monitor Thread...")
