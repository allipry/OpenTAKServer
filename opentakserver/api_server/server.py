#!/usr/bin/env python3
"""
Entry point for the OpenTAKServer API server
"""

import os
import sys
import threading

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from opentakserver.api_server.fixed_server import app, socketio, test_database_connection, test_rabbitmq_connection, broadcast_status_updates, database_connected, rabbitmq_connected

def main():
    print('Fixed OpenTAKServer starting on 0.0.0.0:8080...')
    
    # Test connectivity on startup
    print("Testing service connectivity...")
    test_database_connection()
    test_rabbitmq_connection()
    
    print(f"Database connected: {database_connected}")
    print(f"RabbitMQ connected: {rabbitmq_connected}")
    print("Starting Flask-SocketIO server...")
    
    # Start background status broadcasting
    status_thread = threading.Thread(target=broadcast_status_updates, daemon=True)
    status_thread.start()
    
    try:
        socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()