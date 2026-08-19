// Store already animated/logged request IDs to prevent repeats
const knownRequestIds = new Set();

// SVG coordinates for visualizer layout
const NODE_COORDS = {
    client: { x: 50, y: 140 },
    balancer: { x: 220, y: 140 },
    servers: {
        1: { x: 430, y: 50 },
        2: { x: 430, y: 110 },
        3: { x: 430, y: 170 },
        4: { x: 430, y: 230 }
    }
};

// Chart.js global instances
let chartDist = null;
let chartUtil = null;
let chartLat = null;

// Initialize charts on DOM load
document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    initTopology();
    
    // Start polling data
    pollDashboardData();
    setInterval(pollDashboardData, 1000);
});

// Configure custom Chart.js styles matching Ripe Banana Yellow, Green, and Terracotta palette
function initCharts() {
    const ctxDist = document.getElementById("chart-distribution").getContext("2d");
    chartDist = new Chart(ctxDist, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Requests Count',
                data: [],
                backgroundColor: '#FFD000', // Banana yellow
                borderColor: '#222222',
                borderWidth: 2.5,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: '#EAEAEA' }, ticks: { color: '#555' } },
                x: { ticks: { color: '#555' } }
            }
        }
    });

    const ctxUtil = document.getElementById("chart-utilization").getContext("2d");
    chartUtil = new Chart(ctxUtil, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: ['#E76F51', '#38B000', '#F4A261', '#E9C46A'], // Orange, Green, Amber, Yellow
                borderColor: '#222222',
                borderWidth: 2.5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { family: 'Plus Jakarta Sans' } } } }
        }
    });

    const ctxLat = document.getElementById("chart-latency").getContext("2d");
    chartLat = new Chart(ctxLat, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Avg Response Latency',
                data: [],
                borderColor: '#E76F51', // Orange-red line
                backgroundColor: 'rgba(231, 111, 81, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointRadius: 4,
                pointBackgroundColor: '#222222',
                pointBorderColor: '#222222'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: '#EAEAEA' }, ticks: { color: '#555' } },
                x: { display: false }
            }
        }
    });
}

// Draw base topology layout (Client, Balancer, Server nodes and lines)
function initTopology() {
    const svg = document.getElementById("topology-svg");
    svg.setAttribute("viewBox", "0 0 500 280");
    
    const wiresGroup = document.getElementById("topology-wires");
    
    // Draw connections: Client to Balancer
    const clientToLbPath = `M ${NODE_COORDS.client.x} ${NODE_COORDS.client.y} L ${NODE_COORDS.balancer.x} ${NODE_COORDS.balancer.y}`;
    createWire(wiresGroup, clientToLbPath);

    // Draw connections: Balancer to Servers
    for (let id in NODE_COORDS.servers) {
        const coords = NODE_COORDS.servers[id];
        const path = `M ${NODE_COORDS.balancer.x} ${NODE_COORDS.balancer.y} L ${coords.x} ${coords.y}`;
        createWire(wiresGroup, path);
    }

    renderTopologyNodes([], {});
}

function createWire(parent, pathD) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", pathD);
    parent.appendChild(path);
}

// Render dynamic server states, status indicators, and cute vector icons in topology
function renderTopologyNodes(servers, statusStates) {
    const nodesGroup = document.getElementById("topology-nodes");
    nodesGroup.innerHTML = ""; // Redraw nodes

    // Render Client Node
    const clientNode = createNodeGroup(NODE_COORDS.client.x, NODE_COORDS.client.y, "Client", "#EAEAEA");
    // Client Doodle Icon (Screen)
    clientNode.innerHTML += `
        <rect x="-18" y="-18" width="36" height="26" rx="4" fill="#FFFFFF" stroke="#222" stroke-width="2.5" />
        <line x1="-12" y1="-12" x2="12" y2="-12" stroke="#222" stroke-width="2" />
        <polygon points="-8,8 8,8 -4,15 4,15" fill="#222" stroke="#222" stroke-width="2" />
        <circle cx="0" cy="2" r="2" fill="#52B788" />
    `;
    nodesGroup.appendChild(clientNode);

    // Render Balancer Node
    const balancerNode = createNodeGroup(NODE_COORDS.balancer.x, NODE_COORDS.balancer.y, "Load Balancer", "#FFD000");
    // Cute Load Balancer Router Icon
    balancerNode.innerHTML += `
        <rect x="-22" y="-14" width="44" height="28" rx="6" fill="#FFF" stroke="#222" stroke-width="2.5" />
        <path d="M-15,0 L15,0 M-5,-6 L5,-6 M-8,6 L8,6" stroke="#222" stroke-width="2.5" stroke-linecap="round" />
        <polygon points="12,0 8,-4 8,4" fill="#222" />
        <polygon points="-12,0 -8,-4 -8,4" fill="#222" />
        <circle cx="0" cy="-6" r="2.5" fill="#38B000" />
    `;
    nodesGroup.appendChild(balancerNode);

    // Render Server Nodes
    servers.forEach(server => {
        const coords = NODE_COORDS.servers[server.id];
        if (!coords) return;

        const isHealthy = server.status === "healthy";
        const color = isHealthy ? "#E2F5D9" : "#FFF2F0";
        
        const serverNode = createNodeGroup(coords.x, coords.y, server.name.split(" ")[0], color);
        
        // Cute Mini Server Rack Icon
        serverNode.innerHTML += `
            <rect x="-20" y="-18" width="40" height="36" rx="4" fill="#FFFFFF" stroke="${isHealthy ? '#222' : '#D94E34'}" stroke-width="2.5" />
            <line x1="-15" y1="-10" x2="15" y2="-10" stroke="${isHealthy ? '#222' : '#D94E34'}" stroke-width="2" />
            <line x1="-15" y1="0" x2="15" y2="0" stroke="${isHealthy ? '#222' : '#D94E34'}" stroke-width="2" />
            <line x1="-15" y1="10" x2="15" y2="10" stroke="${isHealthy ? '#222' : '#D94E34'}" stroke-width="2" />
            <!-- LED Dials -->
            <circle cx="10" cy="-10" r="2" fill="${isHealthy ? '#38B000' : '#D94E34'}" />
            <circle cx="10" cy="0" r="2" fill="${isHealthy ? '#38B000' : '#D94E34'}" />
            <circle cx="10" cy="10" r="2" fill="${isHealthy ? '#38B000' : '#D94E34'}" />
        `;
        
        // Add band-aid/failed doodle on server node if offline
        if (!isHealthy) {
            serverNode.innerHTML += `
                <line x1="-14" y1="-14" x2="14" y2="14" stroke="#D94E34" stroke-width="3" />
                <line x1="14" y1="-14" x2="-14" y2="14" stroke="#D94E34" stroke-width="3" />
            `;
        }

        nodesGroup.appendChild(serverNode);
    });
}

function createNodeGroup(x, y, labelText, bgColor) {
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    group.setAttribute("transform", `translate(${x}, ${y})`);

    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("y", "32");
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("fill", "#222");
    text.setAttribute("font-size", "10px");
    text.setAttribute("font-weight", "600");
    text.setAttribute("font-family", "Plus Jakarta Sans");
    text.textContent = labelText;
    group.appendChild(text);

    return group;
}

// Query consolidated stats endpoint and update dashboard components
function pollDashboardData() {
    fetch('/dashboard-data')
        .then(res => res.json())
        .then(data => {
            updateKPIs(data.metrics);
            updateServerControls(data.servers);
            updateAlgorithmUI(data.current_algorithm);
            updateTrafficButtons(data.traffic_sim_active);
            updateTerminal(data.logs);
            updateChartData(data);
            
            // Check for new logs to trigger packet flow animations
            animateNewLogs(data.logs);
            
            // Redraw server nodes in topology SVG
            renderTopologyNodes(data.servers);
        })
        .catch(err => console.error("Error fetching polling data:", err));
}

// Update Top KPI counters
function updateKPIs(metrics) {
    document.getElementById("val-total-requests").innerText = metrics.total_requests;
    
    let rate = 100;
    if (metrics.total_requests > 0) {
        rate = Math.round((metrics.successful_requests / metrics.total_requests) * 100);
    }
    document.getElementById("val-success-rate").innerText = `${rate}%`;
    document.getElementById("val-avg-latency").innerText = metrics.avg_response_time;
    document.getElementById("val-active-connections").innerText = metrics.active_connections;

    // System health banner updates
    const healthBadge = document.getElementById("system-health-badge");
    if (metrics.healthy_servers === 0) {
        healthBadge.innerText = "ALL SERVERS CRASHED";
        healthBadge.className = "badge-status badge-unhealthy";
    } else if (metrics.unhealthy_servers > 0) {
        healthBadge.innerText = "FAILOVER ROUTING ENABLED";
        healthBadge.className = "badge-status";
        healthBadge.style.backgroundColor = "#F4A261"; // Orange warning
        healthBadge.style.color = "white";
    } else {
        healthBadge.innerText = "SYSTEM STABLE";
        healthBadge.className = "badge-status badge-healthy";
        healthBadge.style.backgroundColor = ""; // Reset
    }
}

// Sync selection highlights for routing algorithms
function updateAlgorithmUI(activeAlgo) {
    const list = ["round_robin", "weighted_round_robin", "least_connections"];
    list.forEach(algo => {
        const btn = document.getElementById(`btn-algo-${algo === 'round_robin' ? 'rr' : (algo === 'weighted_round_robin' ? 'wrr' : 'lc')}`);
        if (algo === activeAlgo) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });
}

function updateTrafficButtons(isActive) {
    const btn = document.getElementById("btn-toggle-traffic");
    if (isActive) {
        btn.innerText = "Stop Auto-Traffic";
        btn.className = "banana-btn banana-btn-orange";
    } else {
        btn.innerText = "Start Auto-Traffic";
        btn.className = "banana-btn";
    }
}

// Re-render server list inputs dynamically
function updateServerControls(servers) {
    const container = document.getElementById("servers-container");
    container.innerHTML = ""; // Clear existing

    servers.forEach(server => {
        const isHealthy = server.status === "healthy";
        const cardCol = document.createElement("div");
        cardCol.className = "col-md-3 mb-3";

        // Create Card HTML
        cardCol.innerHTML = `
            <div class="server-card ${isHealthy ? '' : 'unhealthy'} h-100">
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <h5 class="mb-0 text-truncate" title="${server.name}">${server.name}</h5>
                    <span class="badge-status ${isHealthy ? 'badge-healthy' : 'badge-unhealthy'}">
                        ${isHealthy ? 'ONLINE' : 'OFFLINE'}
                    </span>
                </div>
                <div class="text-muted small font-monospace mb-3">${server.url}</div>
                
                <!-- Dynamic Metrics info -->
                <div class="row text-center mb-3">
                    <div class="col-6 border-end">
                        <div class="small text-muted">Active Conn</div>
                        <h4 class="mb-0 fw-bold font-monospace">${server.active_connections}</h4>
                    </div>
                    <div class="col-6">
                        <div class="small text-muted">Weight</div>
                        <h4 class="mb-0 fw-bold font-monospace">${server.weight}</h4>
                    </div>
                </div>

                <!-- Slider Controls -->
                <div class="mb-2">
                    <label class="form-label small fw-bold mb-0">Adjust Capacity Weight:</label>
                    <input type="range" class="banana-slider" min="1" max="10" value="${server.weight}" 
                        onchange="updateWeight(${server.id}, this.value)" ${isHealthy ? '' : 'disabled'}>
                    <div class="d-flex justify-content-between text-muted small" style="font-size: 0.75rem;">
                        <span>1 (Low)</span>
                        <span>10 (High)</span>
                    </div>
                </div>

                <div class="mb-3">
                    <label class="form-label small fw-bold mb-0">Simulated Network Delay:</label>
                    <input type="range" class="banana-slider" min="0" max="2" step="0.1" value="${server.simulated_delay}" 
                        onchange="updateDelay('${server.url}', this.value)" ${isHealthy ? '' : 'disabled'}>
                    <div class="d-flex justify-content-between text-muted small" style="font-size: 0.75rem;">
                        <span>0.0s (None)</span>
                        <span>2.0s (Slow)</span>
                    </div>
                </div>

                <!-- Simulation Action Buttons -->
                <div class="d-grid mt-3">
                    ${isHealthy ? 
                        `<button class="banana-btn banana-btn-orange font-monospace" style="font-size:0.75rem;" onclick="simulateFailure(${server.id})">Simulate Crash</button>` :
                        `<button class="banana-btn font-monospace" style="font-size:0.75rem;" onclick="recoverServer(${server.id})">Recover Server</button>`
                    }
                </div>
            </div>
        `;
        container.appendChild(cardCol);
    });
}

// Append new logs to the scrolling terminal console
function updateTerminal(logs) {
    const consoleBox = document.getElementById("terminal-console");
    
    // We reverse logs so newest print at the bottom of the stack
    const sortedLogs = [...logs].reverse();
    
    sortedLogs.forEach(log => {
        if (!knownRequestIds.has(log.request_id)) {
            // Register as processed
            knownRequestIds.add(log.request_id);
            
            // Format time
            const timestamp = log.timestamp.split(" ")[1] || log.timestamp;
            
            const line = document.createElement("div");
            line.className = "terminal-line";
            
            const isSuccess = log.status_code >= 200 && log.status_code < 400;
            const algoColor = log.algorithm_used === 'least_connections' ? 'log-lc' : (log.algorithm_used === 'round_robin' ? 'log-rr' : 'log-wrr');
            
            let statusText = isSuccess ? `<span class="log-success">SUCCESS (${log.status_code})</span>` : `<span class="log-fail">FAILED (${log.status_code})</span>`;
            let targetText = log.server_name ? `routed to <span class="fw-bold">${log.server_name}</span>` : `<span class="log-fail">NO HEALTHY BACKEND</span>`;
            
            line.innerHTML = `
                <span class="text-muted">[${timestamp}]</span> 
                Req: <span class="text-white">${log.request_id.slice(0, 8)}...</span> 
                Algo: <span class="${algoColor}">${log.algorithm_used.replace('_', ' ').toUpperCase()}</span> - 
                ${targetText} - 
                Latency: <span class="text-warning">${Math.round(log.response_time_ms)}ms</span> - 
                Status: ${statusText}
            `;
            
            consoleBox.appendChild(line);
            // Auto scroll to bottom
            consoleBox.scrollTop = consoleBox.scrollHeight;
        }
    });
}

// Trigger particle animations for newly discovered request transactions
function animateNewLogs(logs) {
    // Only animate if tab is active to save resources
    if (document.hidden) return;

    logs.forEach(log => {
        // If it's a request log and we haven't animated it yet
        if (log.server_id && !knownRequestIds.has(log.request_id)) {
            const serverId = log.server_id;
            // Delay animations slightly so they stream cleanly
            setTimeout(() => {
                triggerRequestAnimation(serverId);
            }, Math.random() * 200);
        }
    });
}

// Animate a yellow request bubble flowing along SVG path Client -> Balancer -> Target Server
function triggerRequestAnimation(serverId) {
    const packetsGroup = document.getElementById("topology-packets");
    const targetCoords = NODE_COORDS.servers[serverId];
    if (!targetCoords) return;

    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("r", "6");
    circle.setAttribute("fill", "#FFD000"); // Banana yellow
    circle.setAttribute("stroke", "#222");
    circle.setAttribute("stroke-width", "2");
    packetsGroup.appendChild(circle);

    const client = NODE_COORDS.client;
    const lb = NODE_COORDS.balancer;

    let progress = 0;
    const duration = 800; // total animation time in ms
    const startTime = performance.now();

    function animateStep(timestamp) {
        const elapsed = timestamp - startTime;
        progress = Math.min(elapsed / duration, 1);

        let currentX, currentY;

        // Stage 1: Client -> Load Balancer (first half of timeline)
        if (progress <= 0.4) {
            const subProgress = progress / 0.4;
            currentX = client.x + (lb.x - client.x) * subProgress;
            currentY = client.y + (lb.y - client.y) * subProgress;
        } 
        // Stage 2: Load Balancer -> Server (second half of timeline)
        else {
            const subProgress = (progress - 0.4) / 0.6;
            currentX = lb.x + (targetCoords.x - lb.x) * subProgress;
            currentY = lb.y + (targetCoords.y - lb.y) * subProgress;
        }

        circle.setAttribute("cx", currentX);
        circle.setAttribute("cy", currentY);

        if (progress < 1) {
            requestAnimationFrame(animateStep);
        } else {
            // Remove circle when animation finishes
            if (circle.parentNode) {
                circle.parentNode.removeChild(circle);
            }
        }
    }

    requestAnimationFrame(animateStep);
}

// Sync dynamic chart metrics
function updateChartData(data) {
    // 1. Traffic Distribution
    const distLabels = Object.keys(data.metrics.distribution);
    const distData = Object.values(data.metrics.distribution);
    
    chartDist.data.labels = distLabels;
    chartDist.data.datasets[0].data = distData;
    chartDist.update();

    // 2. Connections utilization
    const utilLabels = data.servers.map(s => s.name);
    const utilData = data.servers.map(s => s.active_connections);
    
    chartUtil.data.labels = utilLabels;
    chartUtil.data.datasets[0].data = utilData;
    chartUtil.update();

    // 3. Response latency history
    const historyTimes = data.history.map(h => {
        const t = h.timestamp.split(" ")[1] || h.timestamp;
        return t;
    });
    const historyAvg = data.history.map(h => h.avg_response_time);
    
    chartLat.data.labels = historyTimes;
    chartLat.data.datasets[0].data = historyAvg;
    chartLat.update();
}

// API Post Helpers

function setAlgorithm(algo) {
    fetch('/set-algorithm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ algorithm: algo })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === "success") {
            pollDashboardData();
        }
    });
}

function sendSingleRequest() {
    fetch('/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload: "Single Client Sandbox Request" })
    })
    .then(res => res.json())
    .then(data => {
        pollDashboardData();
    });
}

function toggleTrafficSimulation() {
    const btn = document.getElementById("btn-toggle-traffic");
    const rateSelect = document.getElementById("select-traffic-rate");
    const isActive = btn.innerText === "Stop Auto-Traffic";
    
    fetch('/simulate-traffic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            active: !isActive,
            rate: parseInt(rateSelect.value)
        })
    })
    .then(res => res.json())
    .then(data => {
        pollDashboardData();
    });
}

function simulateFailure(serverId) {
    fetch('/simulate-failure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ server_id: serverId })
    })
    .then(res => res.json())
    .then(data => {
        pollDashboardData();
    });
}

function recoverServer(serverId) {
    fetch('/recover-server', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ server_id: serverId })
    })
    .then(res => res.json())
    .then(data => {
        pollDashboardData();
    });
}

function updateWeight(serverId, weight) {
    fetch('/update-weight', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ server_id: serverId, weight: parseInt(weight) })
    })
    .then(res => res.json())
    .then(data => {
        pollDashboardData();
    });
}

function updateDelay(url, delaySeconds) {
    // Send simulated delay parameter to mock manager
    fetch('/servers')
        .then(res => res.json())
        .then(servers => {
            const target = servers.find(s => s.url === url);
            if (target) {
                // Update via helper or custom route
                // We'll simulate delay by writing a small API post or handle it inline.
                // In our Python server manager, we can provide a small helper.
                // Let's create an endpoint in dashboard.py to update simulated delay!
                // Wait! Let's verify if dashboard.py has a route to update delay.
                // Ah! We didn't define POST /update-delay in dashboard.py, but we can easily add it or route it.
                // Let's create a POST /update-delay API call!
                // First, let's write the fetch logic here, then we will use replace_file_content to add it to dashboard.py if needed.
                fetch('/update-delay', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url, delay: parseFloat(delaySeconds) })
                })
                .then(res => res.json())
                .then(() => pollDashboardData());
            }
        });
}
