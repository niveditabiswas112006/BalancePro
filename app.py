import os
import atexit
from flask import Flask

import database
import server_manager
from health_monitor import HealthMonitor

def create_app():
    # Setup paths relative to project root
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # Initialize SQLite Database
    print("[*] Initializing Database...")
    database.init_db()
    database.reset_all_connections()

    # Get server list to spin them up
    servers = database.get_servers()

    # Start mock HTTP servers on ports 5001-5004
    print("[*] Spinning up Mock HTTP Backend Servers...")
    server_manager.start_all_mock_servers(servers)

    # Start the daemon Health Monitor thread
    print("[*] Launching Health Monitoring Thread...")
    health_checker = HealthMonitor(interval=5)
    health_checker.start()

    # Register API blueprint
    from dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    # Clean shutdown hook for threads
    def cleanup():
        print("\n[*] Shutting down BalancePro load balancer services...")
        server_manager.stop_all_mock_servers()
        health_checker.stop()
        print("[*] Teardown complete. Exiting.")

    atexit.register(cleanup)

    return app

if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*50)
    print(" BALANCEPRO IS READY TO ROUTE TRAFFIC!")
    print(" Dashboard URL: http://127.0.0.1:8080/")
    print("="*50 + "\n")
    
    # Run the Flask App
    try:
        app.run(host='127.0.0.1', port=8080, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        pass
