#!/usr/bin/env python3
"""
Marti API Registration Endpoints
Integrates with existing TAK Server group and enrollment systems
Follows /Marti/api/* pattern for consistency
"""

from flask import Blueprint, jsonify, request
import logging
import uuid
import json
import os
import secrets
import psycopg2
from opentakserver.magk.services.teams import get_teams_from_db
from opentakserver.magk.services.database import get_database_connection

# Create blueprint following Marti API pattern
marti_registration_bp = Blueprint('marti_registration', __name__, url_prefix='/Marti/api/registration')

logger = logging.getLogger(__name__)

@marti_registration_bp.route('/groups/available', methods=['GET'])
def get_available_groups():
    """
    Get groups available for registration
    Follows Marti API pattern: /Marti/api/registration/groups/available
    """
    try:
        logger.info("Marti Registration: Getting available groups for registration")
        
        # SOKOL teams only - no default teams
        groups_data = [
            {
                "id": 1,
                "name": "Liberation Front",
                "description": "Freedom fighters working to liberate occupied territories (Green Camo)",
                "color": "#228B22",
                "active": True,
                "type": "tactical"
            },
            {
                "id": 2,
                "name": "Federal Enforcement Division",
                "description": "Elite enforcement unit maintaining order and control (Tan Camo)",
                "color": "#D2B48C",
                "active": True,
                "type": "tactical"
            }
        ]
        
        # Return both Marti API format and UI-compatible format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.groups.Group",
            "data": groups_data,
            "nodeId": "opentakserver-registration",
            # UI compatibility
            "status": "success",
            "teams": groups_data  # UI expects 'teams' field
        }
        
        logger.info(f"Marti Registration: Returning {len(groups_data)} available groups")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Registration: Error getting available groups: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException", 
            "data": {"message": f"Failed to retrieve available groups: {str(e)}"},
            "nodeId": "opentakserver-registration"
        }), 500

@marti_registration_bp.route('/events/available', methods=['GET'])
def get_available_events():
    """
    Get events available for registration
    Follows Marti API pattern: /Marti/api/registration/events/available
    """
    try:
        logger.info("Marti Registration: Getting available events for registration")
        
        # SOKOL event only - no default events
        events_data = [
            {
                "id": 1,
                "name": "SOKOL",
                "description": "SOKOL tactical exercise - Liberation vs Federal Enforcement",
                "type": "exercise",
                "active": True
            }
        ]
        
        # Return both Marti API format and UI-compatible format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.events.Event", 
            "data": events_data,
            "nodeId": "opentakserver-registration",
            # UI compatibility
            "status": "success",
            "events": events_data  # UI expects 'events' field
        }
        
        logger.info(f"Marti Registration: Returning {len(events_data)} available events")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Registration: Error getting available events: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve available events: {str(e)}"},
            "nodeId": "opentakserver-registration"
        }), 500

# UI-compatible endpoint that returns events in the format expected by the UI
@marti_registration_bp.route('/ui/events', methods=['GET'])
def get_ui_compatible_events():
    """
    UI-compatible events endpoint
    Returns events in the format expected by the OpenTAKServer UI
    Maps to /Marti/api/registration/ui/events
    """
    try:
        logger.info("Marti Registration: Getting UI-compatible events")
        
        # SOKOL event only - matches get_available_events
        events_data = [
            {
                "id": 1,
                "name": "SOKOL",
                "description": "SOKOL tactical exercise - Liberation vs Federal Enforcement",
                "type": "exercise",
                "active": True
            }
        ]
        
        # Return in UI-compatible format
        response = {
            "success": True,
            "data": events_data,
            "message": f"Found {len(events_data)} available events"
        }
        
        logger.info(f"Marti Registration: Returning {len(events_data)} UI-compatible events")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Registration: Error getting UI-compatible events: {e}")
        return jsonify({
            "success": False,
            "error": {
                "message": "Failed to retrieve available events",
                "code": "EVENTS_UNAVAILABLE"
            }
        }), 500

# UI-compatible endpoint for getting teams for a specific event
@marti_registration_bp.route('/ui/events/<int:event_id>/teams', methods=['GET'])
def get_ui_event_teams(event_id):
    """
    UI-compatible teams endpoint for a specific event
    Returns teams in the format expected by the OpenTAKServer UI
    Maps to /Marti/api/registration/ui/events/{event_id}/teams
    """
    try:
        logger.info(f"Marti Registration: Getting UI-compatible teams for event {event_id}")
        
        # SOKOL teams only - all events use the same teams
        teams_data = [
            {
                "id": 1,
                "name": "Liberation Front",
                "description": "Freedom fighters working to liberate occupied territories (Green Camo)",
                "type": "tactical",
                "maxMembers": 15
            },
            {
                "id": 2,
                "name": "Federal Enforcement Division",
                "description": "Elite enforcement unit maintaining order and control (Tan Camo)",
                "type": "tactical",
                "maxMembers": 15
            }
        ]
        
        # Return in UI-compatible format
        response = {
            "success": True,
            "data": teams_data,
            "message": f"Found {len(teams_data)} available teams for event {event_id}"
        }
        
        logger.info(f"Marti Registration: Returning {len(teams_data)} UI-compatible teams for event {event_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Registration: Error getting UI-compatible teams for event {event_id}: {e}")
        return jsonify({
            "success": False,
            "error": {
                "message": "Failed to retrieve available teams",
                "code": "TEAMS_UNAVAILABLE"
            }
        }), 500

# Test endpoint to send email to existing user
@marti_registration_bp.route('/test/send-email/<username>', methods=['POST'])
def test_send_email(username):
    """
    Test endpoint to send registration email to an existing user
    """
    try:
        logger.info(f"Marti Registration: Testing email send to user {username}")
        
        # Get user data from database
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Get user with team and registration info
        cursor.execute("""
            SELECT 
                u.id, u.username, u.email, u.first_name, u.last_name,
                t.id as team_id, t.name as team_name,
                rl.registration_data
            FROM users u
            LEFT JOIN user_teams ut ON u.id = ut.user_id
            LEFT JOIN teams t ON ut.team_id = t.id
            LEFT JOIN registration_logs rl ON u.id = rl.user_id
            WHERE u.username = %s
            ORDER BY rl.created_at DESC
            LIMIT 1
        """, (username,))
        
        user_row = cursor.fetchone()
        
        if not user_row:
            cursor.close()
            conn.close()
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": f"User {username} not found"},
                "nodeId": "opentakserver-registration"
            }), 404
        
        # Parse registration data
        try:
            if user_row[7]:
                if isinstance(user_row[7], str):
                    registration_data = json.loads(user_row[7])
                else:
                    registration_data = user_row[7]  # Already a dict
            else:
                registration_data = {}
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Could not parse registration data for {username}: {e}")
            registration_data = {}
        
        # Get event info
        event_id = registration_data.get('event', 1)  # Default to SOKOL (now ID 1)
        cursor.execute("SELECT id, name FROM events WHERE id = %s", (event_id,))
        event_row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        # Prepare data for email
        user_data = {
            'callsign': user_row[1],
            'name': f"{user_row[3]} {user_row[4]}".strip(),
            'email': user_row[2],
            'deviceType': registration_data.get('phoneOS', 'android')
        }
        
        team_data = {
            'id': user_row[5] or 1,
            'name': user_row[6] or 'Blue Team'
        }
        
        event_data = {
            'id': event_row[0] if event_row else 1,
            'name': event_row[1] if event_row else 'SOKOL'
        }
        
        # Generate a new temporary password for testing
        import secrets
        temp_password = secrets.token_urlsafe(12)
        
        # Send email
        from opentakserver.magk.services.email import email_service
        email_sent = email_service.send_registration_email(user_data, team_data, event_data, temp_password)
        
        if email_sent:
            logger.info(f"Marti Registration: Test email sent successfully to {user_data['email']}")
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.registration.EmailTest",
                "data": {
                    "username": username,
                    "email": user_data['email'],
                    "emailSent": True,
                    "tempPassword": temp_password,
                    "message": "Test email sent successfully"
                },
                "nodeId": "opentakserver-registration"
            }), 200
        else:
            logger.error(f"Marti Registration: Failed to send test email to {user_data['email']}")
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Failed to send test email"},
                "nodeId": "opentakserver-registration"
            }), 500
            
    except Exception as e:
        logger.error(f"Marti Registration: Error in test email send: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Test email failed: {str(e)}"},
            "nodeId": "opentakserver-registration"
        }), 500

@marti_registration_bp.route('/participant', methods=['POST'])
def register_participant():
    """
    Register a new participant for TAK operations
    Integrates with existing user, team, and event systems
    Follows Marti API pattern: /Marti/api/registration/participant
    """
    try:
        data = request.get_json()
        logger.info("Marti Registration: Processing participant registration")
        logger.info(f"Marti Registration: Received data: {data}")
        
        if not data:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Registration data is required"},
                "nodeId": "opentakserver-registration"
            }), 400
        
        # Map UI field names to expected backend field names
        mapped_data = {
            'fullName': data.get('fullName'),
            'callsign': data.get('callsign'),
            'email': data.get('email'),
            'team': data.get('team'),  # UI sends 'team'
            'phoneOS': data.get('phoneOS'),  # UI sends 'phoneOS'
            'event': data.get('event')
        }
        
        # Validate required fields (using UI field names)
        required_fields = ['fullName', 'callsign', 'email', 'team', 'phoneOS']
        missing_fields = [field for field in required_fields if not mapped_data.get(field)]
        
        if missing_fields:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": f"Missing required fields: {', '.join(missing_fields)}"},
                "nodeId": "opentakserver-registration"
            }), 400
        
        # Check if user already exists using Flask-Security
        from flask import current_app
        user_datastore = current_app.security.datastore
        
        existing_user = user_datastore.find_user(username=mapped_data['callsign']) or user_datastore.find_user(email=mapped_data['email'])
        
        if existing_user:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "User with this callsign or email already exists"},
                "nodeId": "opentakserver-registration"
            }), 409
        
        # For now, use static team and event info (can be enhanced later with database queries)
        team_info = (mapped_data['team'], f"Team {mapped_data['team']}")
        event_info = (mapped_data.get('event', 1), "Default Operation")
        
        # Split full name into first and last name
        name_parts = mapped_data['fullName'].strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Generate temporary password
        import secrets
        temp_password = secrets.token_urlsafe(12)
        
        # Create user using Flask-Security's user_datastore (proper way)
        from flask import current_app
        user_datastore = current_app.security.datastore
        
        # Create user with Flask-Security (only using fields that exist in the User model)
        user = user_datastore.create_user(
            username=mapped_data['callsign'],
            email=mapped_data['email'],
            password=temp_password,  # Flask-Security will hash this properly
            active=True
        )
        
        # Assign default user role
        user_role = user_datastore.find_role('user')
        if user_role:
            user_datastore.add_role_to_user(user, user_role)
        
        # Commit the user creation
        user_datastore.commit()
        user_id = user.id
        
        # Team assignment and logging can be added later with proper models
        # For now, the user is created and can authenticate for certificate signing
        logger.info(f"User {mapped_data['callsign']} created successfully with Flask-Security")
        
        # Create participant response data
        participant_data = {
            "uid": str(user_id),
            "callsign": mapped_data['callsign'],
            "name": mapped_data['fullName'],
            "email": mapped_data['email'],
            "team": {
                "id": team_info[0],
                "name": team_info[1]
            },
            "event": {
                "id": event_info[0],
                "name": event_info[1]
            },
            "deviceType": mapped_data['phoneOS'],
            "status": "registered",
            "tempPassword": temp_password,  # Include temporary password for initial setup
            "created": "2025-10-05T21:30:00Z"
        }
        
        # Send registration email
        email_sent = False
        try:
            from opentakserver.magk.services.email import email_service
            
            user_data = {
                'callsign': mapped_data['callsign'],
                'name': mapped_data['fullName'],
                'email': mapped_data['email'],
                'deviceType': mapped_data['phoneOS']
            }
            
            team_data = {
                'id': team_info[0],
                'name': team_info[1]
            }
            
            event_data = {
                'id': event_info[0],
                'name': event_info[1]
            }
            
            email_sent = email_service.send_registration_email(user_data, team_data, event_data, temp_password)
            
            if email_sent:
                logger.info(f"Marti Registration: Email sent successfully to {mapped_data['email']}")
                participant_data["emailSent"] = True
            else:
                logger.warning(f"Marti Registration: Failed to send email to {mapped_data['email']}")
                participant_data["emailSent"] = False
                
        except Exception as e:
            logger.error(f"Marti Registration: Error sending email to {mapped_data['email']}: {e}")
            participant_data["emailSent"] = False
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.registration.Participant",
            "data": participant_data,
            "nodeId": "opentakserver-registration"
        }
        
        logger.info(f"Marti Registration: Participant registered successfully - {mapped_data['callsign']} (User ID: {user_id}) - Email sent: {email_sent}")
        return jsonify(response), 201
        
    except Exception as e:
        logger.error(f"Marti Registration: Error registering participant: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Registration failed: {str(e)}"},
            "nodeId": "opentakserver-registration"
        }), 500

@marti_registration_bp.route('/events/available/<int:event_id>/groups/available', methods=['GET'])
def get_groups_for_event(event_id):
    """
    Get groups available for a specific event
    Follows Marti API pattern: /Marti/api/registration/events/available/{id}/groups/available
    """
    try:
        logger.info(f"Marti Registration: Getting groups for event {event_id}")
        
        # For now, return all available groups for any event
        # In the future, this could be enhanced to support event-specific groups
        from opentakserver.magk.services.teams import get_teams_from_db
        teams = get_teams_from_db()
        
        # Format as groups data
        groups_data = []
        for team in teams:
            groups_data.append({
                "id": team["id"],
                "name": team["name"],
                "description": team["description"],
                "color": team["color"],
                "active": team["is_active"],
                "type": team["team_type"]
            })
        
        # Return both Marti API format and UI-compatible format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.groups.Group",
            "data": groups_data,
            "nodeId": "opentakserver-registration",
            # UI compatibility
            "status": "success",
            "teams": groups_data  # UI expects 'teams' field
        }
        
        logger.info(f"Marti Registration: Returning {len(groups_data)} groups for event {event_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Registration: Error getting groups for event {event_id}: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve groups for event: {str(e)}"},
            "nodeId": "opentakserver-registration"
        }), 500

@marti_registration_bp.route('/status/<registration_id>', methods=['GET'])
def get_registration_status(registration_id):
    """
    Get registration status for a participant
    Follows Marti API pattern: /Marti/api/registration/status/<id>
    """
    try:
        logger.info(f"Marti Registration: Getting status for registration {registration_id}")
        
        # In real implementation, this would query the database
        status_data = {
            "uid": registration_id,
            "status": "pending_enrollment",
            "message": "Registration received. Awaiting certificate generation.",
            "enrollmentUrl": f"/Marti/api/tls/profile/enrollment?token={registration_id}",
            "updated": "2025-10-05T21:30:00Z"
        }
        
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.registration.Status",
            "data": status_data,
            "nodeId": "opentakserver-registration"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Registration: Error getting registration status: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to get registration status: {str(e)}"},
            "nodeId": "opentakserver-registration"
        }), 500

@marti_registration_bp.route('/health', methods=['GET'])
def registration_health():
    """
    Health check for registration system
    Follows Marti API pattern: /Marti/api/registration/health
    """
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.health.Status",
        "data": {
            "status": "healthy",
            "service": "marti-registration",
            "version": "1.0.0",
            "timestamp": "2025-10-05T21:30:00Z"
        },
        "nodeId": "opentakserver-registration"
    }), 200

# Error handlers following Marti API pattern
@marti_registration_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.NotFoundException",
        "data": {"message": "Registration endpoint not found"},
        "nodeId": "opentakserver-registration"
    }), 404

@marti_registration_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "version": "3", 
        "type": "com.bbn.marti.remote.exception.MethodNotAllowedException",
        "data": {"message": "Method not allowed"},
        "nodeId": "opentakserver-registration"
    }), 405

@marti_registration_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.TakException", 
        "data": {"message": "Internal server error"},
        "nodeId": "opentakserver-registration"
    }), 500