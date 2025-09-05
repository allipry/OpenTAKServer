"""
Enhanced API Blueprint for OpenTAKServer Integration
Provides dashboard API endpoints and Socket.IO functionality
"""

from flask import Blueprint, jsonify, request
from flask_socketio import emit
import psutil
import time
import os
from datetime import datetime, timezone

enhanced_api = Blueprint('enhanced_api', __name__)

# System metrics cache
_metrics_cache = {}
_cache_timestamp = 0
CACHE_DURATION = 5

def get_system_metrics():
    global _metrics_cache, _cache_timestamp
    
    current_time = time.time()
    if current_time - _cache_timestamp > CACHE_DURATION:
        try:
            _metrics_cache = {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory': psutil.virtual_memory()._asdict(),
                'disk': psutil.disk_usage('/')._asdict(),
                'timestamp': current_time
            }
        except:
            _metrics_cache = {
                'cpu_percent': 0,
                'memory': {'percent': 0},
                'disk': {'used': 0, 'total': 1},
                'timestamp': current_time
            }
        _cache_timestamp = current_time
    
    return _metrics_cache

@enhanced_api.route('/health')
def health_check():
    """Health check endpoint for container health checks"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()})

@enhanced_api.route('/api/status')
def api_status():
    try:
        metrics = get_system_metrics()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system': {
                'cpu_percent': metrics['cpu_percent'],
                'memory_percent': metrics['memory']['percent'],
                'disk_percent': (metrics['disk']['used'] / metrics['disk']['total']) * 100,
                'uptime': time.time() - psutil.boot_time() if hasattr(psutil, 'boot_time') else 0
            },
            'services': {
                'database': 'connected',
                'rabbitmq': 'connected'
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@enhanced_api.route('/api/itak_qr_string', methods=['GET', 'POST'])
def itak_qr_string():
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            username = data.get('username', 'user')
            token = data.get('token', 'password')
        else:
            username = request.args.get('username', 'user')
            token = request.args.get('token', 'password')
        
        server_host = os.getenv('EXTERNAL_HOST', request.host.split(':')[0])
        qr_string = f"tak://com.atakmap.app/enroll?host={server_host}&username={username}&token={token}"
        
        return jsonify({
            'qr_string': qr_string,
            'username': username,
            'server': server_host
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@enhanced_api.route('/api/atak_qr_string', methods=['GET', 'POST'])
def atak_qr_string():
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            expiry = data.get('expiry', '2024-12-31')
            max_uses = data.get('max_uses', 10)
        else:
            expiry = request.args.get('expiry', '2024-12-31')
            max_uses = request.args.get('max_uses', 10)
        
        server_host = os.getenv('EXTERNAL_HOST', request.host.split(':')[0])
        qr_string = f"https://{server_host}:8443/Marti/api/tls/config?expiry={expiry}&max_uses={max_uses}"
        
        return jsonify({
            'qr_string': qr_string,
            'expiry': expiry,
            'max_uses': max_uses,
            'server': server_host
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@enhanced_api.route('/metrics')
def prometheus_metrics():
    try:
        metrics = get_system_metrics()
        
        metrics_text = f"""# HELP cpu_usage_percent CPU usage percentage
# TYPE cpu_usage_percent gauge
cpu_usage_percent {metrics['cpu_percent']}

# HELP memory_usage_percent Memory usage percentage  
# TYPE memory_usage_percent gauge
memory_usage_percent {metrics['memory']['percent']}

# HELP disk_usage_percent Disk usage percentage
# TYPE disk_usage_percent gauge
disk_usage_percent {(metrics['disk']['used'] / metrics['disk']['total']) * 100}
"""
        
        return metrics_text, 200, {'Content-Type': 'text/plain'}
    except Exception as e:
        return f"# Error generating metrics: {str(e)}", 500, {'Content-Type': 'text/plain'}

def register_socketio_events(socketio):
    @socketio.on('connect')
    def handle_connect():
        emit('status', {'message': 'Connected to OpenTAKServer'})
    
    @socketio.on('request_status')
    def handle_status_request():
        try:
            metrics = get_system_metrics()
            emit('status_update', {
                'cpu_percent': metrics['cpu_percent'],
                'memory_percent': metrics['memory']['percent'],
                'disk_percent': (metrics['disk']['used'] / metrics['disk']['total']) * 100,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            emit('error', {'message': str(e)})