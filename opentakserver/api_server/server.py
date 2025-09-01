#!/usr/bin/env python3
"""
Entry point for the OpenTAKServer API server
"""

import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

from opentakserver.api_server.fixed_server import app, socketio, main

if __name__ == '__main__':
    main()