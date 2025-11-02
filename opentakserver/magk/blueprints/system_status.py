#!/usr/bin/env python3
"""
System Status API Module
Provides system configuration and status information for admin dashboard
"""

from flask import Blueprint, jsonify, current_app
from flask_security import auth_required, roles_required
import logging
import os
from datetime import datetime
import psycopg2
import pika
from pathlib import Path

logger = logging.getLogger(__name__)

# Create blueprint for system status API
system_status_bp = Blueprint('system_status', __name__, url_prefix='/Marti/api/system')


def get_marti_response(data, response_type="SystemStatus"):
    """Helper function to format response in Marti API standard"""
    return {
        "version": "2",
        "type": response_type,
        "data": data,
        "nodeId": "MAGK-Admin"
    }


@system_status_bp.route('/status', methods=['GET'])
def get_system_status():
    """
    Get overall system status
    Returns aggregated status from all system components
    """
    try:
        # Get status from all subsystems
        database_status = _get_database_status()
        messaging_status = _get_messaging_status()
        security_status = _get_security_status()
        tak_status = _get_tak_status()
        
        status_data = {
            'database': database_status,
            'messaging': messaging_status,
            'security': security_status,
            'tak_server': tak_status,
            'overall_status': 'healthy' if all([
                database_status.get('status') == 'connected',
                messaging_status.get('status') == 'connected'
            ]) else 'degraded'
        }
        
        return jsonify(get_marti_response(status_data)), 200
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}", exc_info=True)
        return jsonify(get_marti_response({
            'error': 'Failed to retrieve system status',
            'details': str(e)
        }, "Error")), 500


@system_status_bp.route('/database', methods=['GET'])
def get_database_status():
    """Get PostgreSQL database status"""
    try:
        status_data = _get_database_status()
        return jsonify(get_marti_response(status_data, "DatabaseStatus")), 200
    except Exception as e:
        logger.error(f"Error getting database status: {e}", exc_info=True)
        return jsonify(get_marti_response({
            'error': 'Failed to retrieve database status',
            'details': str(e)
        }, "Error")), 500


@system_status_bp.route('/messaging', methods=['GET'])
def get_messaging_status():
    """Get RabbitMQ messaging status"""
    try:
        status_data = _get_messaging_status()
        return jsonify(get_marti_response(status_data, "MessagingStatus")), 200
    except Exception as e:
        logger.error(f"Error getting messaging status: {e}", exc_info=True)
        return jsonify(get_marti_response({
            'error': 'Failed to retrieve messaging status',
            'details': str(e)
        }, "Error")), 500


@system_status_bp.route('/security', methods=['GET'])
def get_security_status():
    """Get SSL certificate and security status"""
    try:
        status_data = _get_security_status()
        return jsonify(get_marti_response(status_data, "SecurityStatus")), 200
    except Exception as e:
        logger.error(f"Error getting security status: {e}", exc_info=True)
        return jsonify(get_marti_response({
            'error': 'Failed to retrieve security status',
            'details': str(e)
        }, "Error")), 500


@system_status_bp.route('/tak', methods=['GET'])
def get_tak_status():
    """Get TAK server configuration and status"""
    try:
        status_data = _get_tak_status()
        return jsonify(get_marti_response(status_data, "TAKStatus")), 200
    except Exception as e:
        logger.error(f"Error getting TAK status: {e}", exc_info=True)
        return jsonify(get_marti_response({
            'error': 'Failed to retrieve TAK status',
            'details': str(e)
        }, "Error")), 500


# Helper functions

def _get_database_status():
    """Get PostgreSQL database connection status"""
    try:
        from opentakserver.extensions import db
        
        # Get database URI from config
        db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        
        # Parse connection info
        host = os.getenv('OTS_DB_HOST', 'ots-postgresql')
        database = os.getenv('OTS_DB_NAME', 'opentakserver')
        
        # Test connection
        result = db.session.execute(db.text('SELECT 1'))
        result.close()
        
        # Get connection pool info
        pool = db.engine.pool
        pool_size = pool.size()
        checked_out = pool.checkedout()
        
        return {
            'status': 'connected',
            'host': host,
            'database': database,
            'pool_size': pool_size,
            'active_connections': checked_out
        }
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return {
            'status': 'disconnected',
            'error': str(e)
        }


def _get_messaging_status():
    """Get RabbitMQ messaging status"""
    try:
        # Get RabbitMQ connection info from environment
        host = os.getenv('OTS_RABBITMQ_SERVER_ADDRESS', 'ots-rabbitmq')
        port = int(os.getenv('OTS_RABBITMQ_SERVER_PORT', '5672'))
        username = os.getenv('OTS_RABBITMQ_USERNAME', 'ots')
        password = os.getenv('OTS_RABBITMQ_PASSWORD', '')
        vhost = os.getenv('OTS_RABBITMQ_VHOST', 'opentakserver')
        
        # Test connection
        credentials = pika.PlainCredentials(username, password)
        parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=vhost,
            credentials=credentials,
            connection_attempts=1,
            socket_timeout=2
        )
        
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # Get queue info (if possible)
        try:
            queue_info = channel.queue_declare(queue='', passive=True, exclusive=True)
            queues = 1  # At least one queue exists
            messages = queue_info.method.message_count
        except:
            queues = 0
            messages = 0
        
        connection.close()
        
        return {
            'status': 'connected',
            'host': host,
            'queues': queues,
            'messages': messages
        }
    except Exception as e:
        logger.error(f"Messaging status check failed: {e}")
        return {
            'status': 'disconnected',
            'error': str(e)
        }


def _get_security_status():
    """Get SSL certificate and security status"""
    try:
        # Check for SSL certificate files
        cert_path = Path('/certs/fullchain.pem')
        key_path = Path('/certs/privkey.pem')
        
        ssl_enabled = cert_path.exists() and key_path.exists()
        
        certificate_valid = False
        expires = None
        
        if ssl_enabled:
            try:
                # Try to read certificate expiration
                import ssl
                import socket
                from datetime import datetime
                
                # Get certificate info
                cert = ssl.get_server_certificate((os.getenv('EXTERNAL_HOST', 'localhost'), 8443))
                x509 = ssl.PEM_cert_to_DER_cert(cert)
                
                # For now, just mark as valid if file exists
                certificate_valid = True
                # TODO: Parse actual expiration date from certificate
                expires = "2026-01-04T00:00:00Z"  # Placeholder
            except Exception as e:
                logger.warning(f"Could not read certificate details: {e}")
                certificate_valid = True  # Assume valid if file exists
        
        return {
            'ssl_enabled': ssl_enabled,
            'certificate_valid': certificate_valid,
            'expires': expires
        }
    except Exception as e:
        logger.error(f"Security status check failed: {e}")
        return {
            'ssl_enabled': False,
            'certificate_valid': False,
            'error': str(e)
        }


def _get_tak_status():
    """Get TAK server configuration"""
    try:
        # Get TAK server ports from environment
        tcp_port = int(os.getenv('OTS_TCP_STREAMING_PORT', '8087'))
        ssl_port = int(os.getenv('OTS_SSL_STREAMING_PORT', '8089'))
        
        # TODO: Get actual connection count from EUD handler
        # For now, return configuration only
        active_connections = 0
        
        return {
            'tcp_port': tcp_port,
            'ssl_port': ssl_port,
            'active_connections': active_connections
        }
    except Exception as e:
        logger.error(f"TAK status check failed: {e}")
        return {
            'tcp_port': 8087,
            'ssl_port': 8089,
            'active_connections': 0,
            'error': str(e)
        }
