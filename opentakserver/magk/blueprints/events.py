#!/usr/bin/env python3
"""
Marti Events API
Manages events/operations for the TAK Server registration system
"""

from flask import Blueprint, jsonify, request
from opentakserver.magk.services.database import get_database_connection
import psycopg2
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Create blueprint for events management
marti_events_bp = Blueprint('marti_events', __name__, url_prefix='/Marti/api/events')

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host="ots-postgresql",
        database="opentakserver", 
        user="ots",
        password="simple123"
    )

@marti_events_bp.route('', methods=['GET'])
def get_events():
    """
    Get all events
    Marti API: /Marti/api/events
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get active events
        cursor.execute("""
            SELECT id, name, description, event_type, is_active, 
                   start_date, end_date, created_at, settings
            FROM events 
            WHERE is_active = true 
            ORDER BY name
        """)
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "event_type": row[3],
                "is_active": row[4],
                "start_date": row[5].isoformat() if row[5] else None,
                "end_date": row[6].isoformat() if row[6] else None,
                "created_at": row[7].isoformat() if row[7] else None,
                "settings": row[8] or {}
            })
        
        cursor.close()
        conn.close()
        
        # Return in Marti API format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.events.EventList",
            "data": events,
            "nodeId": "opentakserver-core"
        }
        
        logger.info(f"Retrieved {len(events)} events from database")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve events: {str(e)}"},
            "nodeId": "opentakserver-core"
        }), 500

@marti_events_bp.route('', methods=['POST'])
def create_event():
    """
    Create a new event
    Marti API: /Marti/api/events
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Event name is required"},
                "nodeId": "opentakserver-core"
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert new event
        import json
        cursor.execute("""
            INSERT INTO events (name, description, event_type, is_active, start_date, end_date, settings)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, description, event_type, is_active, start_date, end_date, created_at, settings
        """, (
            data.get('name'),
            data.get('description'),
            data.get('event_type', 'operational'),
            data.get('is_active', True),
            data.get('start_date'),
            data.get('end_date'),
            json.dumps(data.get('settings', {}))
        ))
        
        row = cursor.fetchone()
        event_data = {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "event_type": row[3],
            "is_active": row[4],
            "start_date": row[5].isoformat() if row[5] else None,
            "end_date": row[6].isoformat() if row[6] else None,
            "created_at": row[7].isoformat() if row[7] else None,
            "settings": row[8] or {}
        }
        
        conn.commit()
        cursor.close()
        conn.close()
        
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.events.Event",
            "data": event_data,
            "nodeId": "opentakserver-core"
        }
        
        logger.info(f"Created event: {data.get('name')}")
        return jsonify(response), 201
        
    except psycopg2.IntegrityError as e:
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": "Event name already exists"},
            "nodeId": "opentakserver-core"
        }), 409
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to create event: {str(e)}"},
            "nodeId": "opentakserver-core"
        }), 500

@marti_events_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """
    Get a specific event by ID
    Marti API: /Marti/api/events/<id>
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, description, event_type, is_active, 
                   start_date, end_date, created_at, settings
            FROM events 
            WHERE id = %s
        """, (event_id,))
        
        row = cursor.fetchone()
        if not row:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.NotFoundException",
                "data": {"message": f"Event with ID {event_id} not found"},
                "nodeId": "opentakserver-core"
            }), 404
        
        event_data = {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "event_type": row[3],
            "is_active": row[4],
            "start_date": row[5].isoformat() if row[5] else None,
            "end_date": row[6].isoformat() if row[6] else None,
            "created_at": row[7].isoformat() if row[7] else None,
            "settings": row[8] or {}
        }
        
        cursor.close()
        conn.close()
        
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.events.Event",
            "data": event_data,
            "nodeId": "opentakserver-core"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting event {event_id}: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve event: {str(e)}"},
            "nodeId": "opentakserver-core"
        }), 500

@marti_events_bp.route('/available', methods=['GET'])
def get_available_events():
    """
    Get events available for registration
    Marti API: /Marti/api/events/available
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get active events suitable for registration
        cursor.execute("""
            SELECT id, name, description, event_type, is_active
            FROM events 
            WHERE is_active = true 
            ORDER BY name
        """)
        
        events = []
        for row in cursor.fetchall():
            events.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "type": row[3],
                "active": row[4]
            })
        
        cursor.close()
        conn.close()
        
        # Return both Marti API format and UI-compatible format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.events.Event",
            "data": events,
            "nodeId": "opentakserver-core",
            # UI compatibility
            "status": "success",
            "events": events  # UI expects 'events' field
        }
        
        logger.info(f"Retrieved {len(events)} available events from database")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting available events: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve available events: {str(e)}"},
            "nodeId": "opentakserver-core"
        }), 500

# Error handlers
@marti_events_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.NotFoundException",
        "data": {"message": "Event endpoint not found"},
        "nodeId": "opentakserver-core"
    }), 404

@marti_events_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "version": "3", 
        "type": "com.bbn.marti.remote.exception.MethodNotAllowedException",
        "data": {"message": "Method not allowed"},
        "nodeId": "opentakserver-core"
    }), 405

@marti_events_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.TakException", 
        "data": {"message": "Internal server error"},
        "nodeId": "opentakserver-core"
    }), 500