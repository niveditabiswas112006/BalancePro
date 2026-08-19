# BalancePro – Intelligent Load Balancing System

BalancePro is an intelligent, fault-tolerant web server load balancer application featuring dynamic traffic routing, continuous background health monitoring, automated failovers, and real-time visualization dashboard. 

The application is written in Python using Flask and SQLite, and the user interface features a playful, warm **Banana & Doodle** light paper theme (free of blue/purple colors) with live SVGs and charts to monitor active connections.

---

## 📖 PROJECT OVERVIEW & PROBLEM STATEMENT

Modern web applications experience uneven workloads and server crashes. BalancePro acts as a reverse proxy load balancer, routing client request payloads across a cluster of mock backend servers. It implements three core scheduling algorithms (Round Robin, Weighted Round Robin, and Least Connections) to prevent server overload, maximize responsiveness, and guarantee high availability.

---

## ⚡ FEATURES

1.  **Multiple Load Balancing Algorithms**:
    *   **Round Robin**: Sequential cycling.
    *   **Weighted Round Robin**: Capacity-aware distribution.
    *   **Least Connections (Production)**: Smart routing to the server with the lowest connection count.
2.  **Continuous Health Checks**: Pings mock servers every 5 seconds.
3.  **Automated Failover & Recovery**: Removes dead servers instantly and restores them when they recover.
4.  **Traffic Simulator**: An in-browser load generator and individual sandbox query sender.
5.  **Interactive Network Visualizer**: An SVG canvas showing live animated packets (bananas 🍌) flowing to server nodes.
6.  **SQLite Logging**: Stores connection loads, latencies, and responses.
7.  **Chart.js Graphs**: Real-time traffic, latency histories, and connection shares.

---

## 🛠️ TECHNOLOGY STACK

*   **Backend**: Python, Flask, SQLite3, Requests
*   **Frontend**: HTML5, CSS3 (Custom warm neobrutalist doodle theme), JavaScript (ES6+), Bootstrap 5, Chart.js
*   **Tools**: VS Code, Git

---

## 📂 FOLDER STRUCTURE

```text
BalancePro/
│
├── app.py                  # Main entry point (starts threads, initializes DB, launches Flask)
├── load_balancer.py        # Core routing algorithms (Round Robin, Weighted, Least Connections)
├── health_monitor.py      # Background thread checking backend server HTTP health status
├── server_manager.py       # Spawns mock HTTP servers on ports 5001-5004 in separate threads
├── database.py             # SQLite helper and schema manager
├── metrics.py              # Performance calculations and metrics storage snapshots
├── dashboard.py            # API endpoints and dashboard page routing controllers
├── requirements.txt        # Project dependencies
├── README.md               # Setup and execution guide
│
├── templates/
│   └── index.html          # Dashboard HTML skeleton with inline SVGs and control layouts
│
├── static/
│   ├── css/
│   │   └── style.css       # Doodle theme styles, neobrutalist borders, cream grids
│   └── js/
│       └── dashboard.js    # Data polling, SVG animators, Chart.js rendering
│
└── docs/
    └── project_documentation.md # Complete submission-ready report text content
```

---

## 🚀 INSTALLATION & SETUP

### Prerequisites
*   Python 3.8 or higher installed on your system.

### 1. Clone or Copy the Project
Ensure all files are placed in the directory `/Users/niveditabiswas/Designing-a-load-balancer/BalancePro`.

### 2. Set Up a Virtual Environment (Optional but Recommended)
Open your terminal in VS Code and run:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install Flask and Requests:
```bash
pip install -r requirements.txt
```

---

## 🖥️ EXECUTION INSTRUCTIONS

To launch the entire load balancing environment (main load balancer, 4 mock servers, background health checker, and dashboard UI):

```bash
python app.py
```

### Console Startup Output:
```text
[*] Initializing Database...
[*] Spinning up Mock HTTP Backend Servers...
[*] Starting Mock Server on 127.0.0.1:5001
[*] Starting Mock Server on 127.0.0.1:5002
[*] Starting Mock Server on 127.0.0.1:5003
[*] Starting Mock Server on 127.0.0.1:5004
[*] Launching Health Monitoring Thread...
[*] Starting Background Health Monitor Thread...

==================================================
 BALANCEPRO IS READY TO ROUTE TRAFFIC!
 Dashboard URL: http://127.0.0.1:8080/
==================================================

 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```

Now, open your browser and navigate to: **[http://127.0.0.1:8080/](http://127.0.0.1:8080/)** to interact with the dashboard.

---

## 🔍 THUNDER CLIENT / CURL API REFERENCE & SANDBOX

You can query the APIs directly using **Thunder Client** inside VS Code or using **curl** in the terminal to capture academic logs.

### 1. Route Request through Load Balancer
*   **Method**: `POST`
*   **URL**: `http://127.0.0.1:8080/request`
*   **Header**: `Content-Type: application/json`
*   **Body (JSON)**:
    ```json
    {
      "payload": "Thunder Client sandbox load test"
    }
    ```
*   **Example Response**:
    ```json
    {
      "status": "success",
      "request_id": "90cf18df-e0b0-4dbb-b27b-05990263f3cc",
      "algorithm_used": "least_connections",
      "routed_to": {
        "id": 1,
        "name": "Server-1 (Alpha)",
        "url": "http://127.0.0.1:5001"
      },
      "response_time_ms": 23.45,
      "status_code": 200,
      "backend_response": {
        "processed_by": "Server on Port 5001",
        "received_data": "Thunder Client sandbox load test",
        "server_port": 5001,
        "status": "success"
      }
    }
    ```

### 2. Simulate Backend Server Crash (Failover Routing Test)
*   **Method**: `POST`
*   **URL**: `http://127.0.0.1:8080/simulate-failure`
*   **Body (JSON)**:
    ```json
    {
      "server_id": 1
    }
    ```
*   **Expected Response**:
    ```json
    {
      "status": "success",
      "server_id": 1,
      "message": "Server Server-1 (Alpha) set to offline. Health checker will trigger failover."
    }
    ```

### 3. Recover Crashed Backend Server
*   **Method**: `POST`
*   **URL**: `http://127.0.0.1:8080/recover-server`
*   **Body (JSON)**:
    ```json
    {
      "server_id": 1
    }
    ```
*   **Expected Response**:
    ```json
    {
      "status": "success",
      "server_id": 1,
      "message": "Server Server-1 (Alpha) set to online. Health checker will recover connection routing."
    }
    ```

### 4. Fetch Real-time System Metrics Summary
*   **Method**: `GET`
*   **URL**: `http://127.0.0.1:8080/metrics`
*   **Expected Response**:
    ```json
    {
      "total_requests": 25,
      "successful_requests": 24,
      "failed_requests": 1,
      "avg_response_time": 45.2,
      "active_connections": 0,
      "healthy_servers": 3,
      "unhealthy_servers": 1,
      "distribution": {
        "Server-1 (Alpha)": 0,
        "Server-2 (Beta)": 12,
        "Server-3 (Gamma)": 8,
        "Server-4 (Delta)": 5
      }
    }
    ```

---

## 📷 SCREENSHOTS GUIDE
For your academic report submission, launch the project, open the web dashboard, and take screenshots of:
1.  **Home Dashboard**: Healthy state showing balanced traffic paths.
2.  **Failover In Action**: Click "Simulate Crash" on Server-1. Observe the server node turn red in the topology graph, showing a crossed indicator, and logs showing traffic routing automatically bypass Server-1 and balance onto Servers 2, 3, and 4.
3.  **Analytics graphs**: The Chart.js graphs reflecting weights, active connections, and latency spikes.

---

## 🚀 GITHUB UPLOAD GUIDE

To publish your project on GitHub, navigate to `/Users/niveditabiswas/Designing-a-load-balancer/BalancePro` and run:

```bash
git init
git add .
git commit -m "Initial commit: BalancePro complete project"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

---

## 👤 AUTHOR
**Submitted in partial fulfillment of Advanced Systems Engineering Coursework.**  
*   **Author:** [Author Details Placeholder]
*   **Date:** June 2026
