import threading

class LoadBalancer:
    def __init__(self):
        self.lock = threading.Lock()
        self.rr_index = 0
        self.wrr_index = 0

    def select_server(self, servers, algorithm="least_connections"):
        """
        Selects a healthy server based on the specified algorithm.
        servers: List of server dictionaries from the database.
        """
        healthy_servers = [s for s in servers if s['status'] == 'healthy']
        
        if not healthy_servers:
            return None

        with self.lock:
            if algorithm == "round_robin":
                return self._round_robin(healthy_servers)
            elif algorithm == "weighted_round_robin":
                return self._weighted_round_robin(healthy_servers)
            elif algorithm == "least_connections":
                return self._least_connections(healthy_servers)
            else:
                # Default fallback
                return self._least_connections(healthy_servers)

    def _round_robin(self, healthy_servers):
        """
        Simple Round Robin algorithm.
        Cycles through servers sequentially.
        """
        # Ensure index is within bounds of current active server list
        self.rr_index = self.rr_index % len(healthy_servers)
        selected = healthy_servers[self.rr_index]
        self.rr_index = (self.rr_index + 1) % len(healthy_servers)
        return selected

    def _weighted_round_robin(self, healthy_servers):
        """
        Weighted Round Robin algorithm.
        Servers with higher weights receive proportionally more requests.
        """
        # Build a sequence of servers repeated by their weight
        weighted_pool = []
        for server in healthy_servers:
            weight = server.get('weight', 1)
            # Guarantee at least weight 1
            weight = max(1, weight)
            weighted_pool.extend([server] * weight)

        if not weighted_pool:
            return healthy_servers[0]

        self.wrr_index = self.wrr_index % len(weighted_pool)
        selected = weighted_pool[self.wrr_index]
        self.wrr_index = (self.wrr_index + 1) % len(weighted_pool)
        return selected

    def _least_connections(self, healthy_servers):
        """
        Least Connections algorithm.
        Routes traffic to the server with the fewest active connections.
        """
        # Find the server with the minimum active connections
        selected = min(healthy_servers, key=lambda s: s.get('active_connections', 0))
        return selected
