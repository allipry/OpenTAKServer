#!/usr/bin/env python3
"""
Events API Module
Provides CRUD operations for event management with team assignments
"""

from flask import Blueprint, jsonify, request, current_app
from marshmallow import Schema, fields, validate, ValidationError, validates, validates_schema
import logging
from datetime import datetime, timezone
from opentakserver.extensions import db
from opentakserver.magk.models.event import Event
from opentakserver.magk.models.event_team import EventTeam
from opentakserver.magk.services.qr_generator import generate_wifi_qr_string, validate_wifi_credentials

logger = logging.getLogger(__name__)

# Create blueprint for events API
events_bp = Blueprint('events', __name__, url_prefix='/Marti/api/events')


def get_marti_response(data, response_type="EventsData"):
    """Helper function to format response in Marti API standard"""
    return {
        "version": "2",
        "type": response_type,
        "data": data,
        "nodeId": "MAGK-Admin"
    }


# Marshmallow schemas for input validation
class EventSchema(Schema):
    """Schema for event creation and updates"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True, validate=validate.Length(max=5000))
    event_type = fields.Str(allow_none=True, validate=validate.Length(max=50))
    start_date = fields.DateTime(required=True)
    end_date = fields.DateTime(required=True)
    location = fields.Str(allow_none=True, validate=validate.Length(max=255))
    wifi_ssid = fields.Str(allow_none=True, validate=validate.Length(max=32))
    wifi_password = fields.Str(allow_none=True, validate=validate.Length(min=8, max=63))
    is_active = fields.Bool(allow_none=True)
    settings = fields.Dict(allow_none=True)
    
    @validates_schema
    def validate_dates(self, data, **kwargs):
        """Validate that end_date is after start_date"""
        if 'start_date' in data and 'end_date' in data:
            if data['end_date'] <= data['start_date']:
                raise ValidationError('end_date must be after start_date')


class EventUpdateSchema(Schema):
    """Schema for event updates (all fields optional)"""
    name = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True, validate=validate.Length(max=5000))
    event_type = fields.Str(allow_none=True, validate=validate.Length(max=50))
    start_date = fields.DateTime()
    end_date = fields.DateTime()
    location = fields.Str(allow_none=True, validate=validate.Length(max=255))
    wifi_ssid = fields.Str(allow_none=True, validate=validate.Length(max=32))
    wifi_password = fields.Str(allow_none=True, validate=validate.Length(min=8, max=63))
    is_active = fields.Bool()
    settings = fields.Dict(allow_none=True)


class TeamAssignmentSchema(Schema):
    """Schema for team assignment to event"""
    team_id = fields.Int(required=True)
    max_participants = fields.Int(allow_none=True, validate=validate.Range(min=1))


# API Endpoints

@events_bp.route('', methods=['GET'])
def list_events():
    """
    GET /Marti/api/events
    List all events with participant counts
    
    Query parameters:
        - active_only (bool): Filter to active events only (default: false)
        - current_only (bool): Filter to currently running events (default: false)
        - upcoming_only (bool): Filter to upcoming events (default: false)
    """
    try:
        # Get query parameters
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        current_only = request.args.get('current_only', 'false').lower() == 'true'
        upcoming_only = request.args.get('upcoming_only', 'false').lower() == 'true'
        
        # Build query based on filters
        if current_only:
            events = Event.get_current_events()
        elif upcoming_only:
            events = Event.get_upcoming_events()
        elif active_only:
            events = Event.get_active_events()
        else:
            events = Event.query.order_by(Event.start_date.desc()).all()
        
        # Convert to dict with participant counts
        events_data = []
        for event in events:
            event_dict = event.to_dict(include_participant_count=True)
            events_data.append(event_dict)
        
        return jsonify(get_marti_response({
            'events': events_data,
            'total': len(events_data)
        })), 200
        
    except Exception as e:
        logger.error(f"Error listing events: {e}", exc_info=True)
        return jsonify(get_marti_response({
            'error': 'Failed to retrieve events',
            'details': str(e)
        }, "Error")), 500


@events_bp.route('', methods=['POST'])
def create_event():
    """
    POST /Marti/api/events
    Create a new event
    
    Request body: EventSchema
    Note: Authentication handled at nginx/proxy level
    """
    
    try:
        # Validate input
        schema = EventSchema()
        data = schema.load(request.get_json())
        
        # Create event
        event = Event.create_event(
            name=data['name'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            description=data.get('description'),
            location=data.get('location'),
            wifi_ssid=data.get('wifi_ssid'),
            wifi_password=data.get('wifi_password'),
            event_type=data.get('event_type', 'game_day'),
            created_by=None,  # Authentication handled at proxy level
            settings=data.get('settings', {})
        )
        
        logger.info(f"Event created: {event.name}")
        
        return jsonify(get_marti_response({
            'event': event.to_dict(include_participant_count=True),
            'message': 'Event created successfully'
        }, "EventCreated")), 201
        
    except ValidationError as e:
        logger.error(f"Validation error creating event: {e.messages}")
        return jsonify(get_marti_response({
            'error': 'Validation error',
            'details': e.messages
        }, "Error")), 400
    except ValueError as e:
        logger.error(f"ValueError creating event: {str(e)}")
        return jsonify(get_marti_response({
            'error': 'Invalid data',
            'details': str(e)
        }, "Error")), 400
    except Exception as e:
        logger.error(f"Error creating event: {e}", exc_info=True)
        db.session.rollback()
        return jsonify(get_marti_response({
            'error': 'Failed to create event',
            'details': str(e)
        }, "Error")), 500


@events_bp.route('/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """
    GET /Marti/api/events/<id>
    Get event details including teams and participant count
    """
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify(get_marti_response({
                'error': 'Event not found',
                'event_id': event_id
            }, "Error")), 404
        
        return jsonify(get_marti_response({
            'event': event.to_dict(include_teams=True, include_participant_count=True)
        })), 200
        
    except Exception as e:
        logger.error(f"Error getting event {event_id}: {e}", exc_info=True)
        return jsonify(get_marti_response({
            'error': 'Failed to retrieve event',
            'details': str(e)
        }, "Error")), 500


@events_bp.route('/<int:event_id>', methods=['PUT'])
def update_event(event_id):
    """
    PUT /Marti/api/events/<id>
    Update event (admin only)
    
    Request body: EventUpdateSchema
    """
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify(get_marti_response({
                'error': 'Event not found',
                'event_id': event_id
            }, "Error")), 404
        
        # Validate input
        schema = EventUpdateSchema()
        data = schema.load(request.get_json())
        
        # Update fields
        if 'name' in data:
            event.name = data['name']
        if 'description' in data:
            event.description = data['description']
        if 'event_type' in data:
            event.event_type = data['event_type']
        if 'start_date' in data:
            event.start_date = data['start_date']
        if 'end_date' in data:
            event.end_date = data['end_date']
        if 'location' in data:
            event.location = data['location']
        if 'wifi_ssid' in data:
            event.wifi_ssid = data['wifi_ssid']
        if 'wifi_password' in data:
            event.wifi_password = data['wifi_password']
        if 'is_active' in data:
            event.is_active = data['is_active']
        if 'settings' in data:
            event.settings = data['settings']
        
        # Validate dates if both are present
        if event.start_date and event.end_date:
            is_valid, error_message = event.validate_dates()
            if not is_valid:
                return jsonify(get_marti_response({
                    'error': error_message
                }, "Error")), 400
        
        db.session.commit()
        
        logger.info(f"Event updated: {event.name}")
        
        return jsonify(get_marti_response({
            'event': event.to_dict(include_participant_count=True),
            'message': 'Event updated successfully'
        }, "EventUpdated")), 200
        
    except ValidationError as e:
        return jsonify(get_marti_response({
            'error': 'Validation error',
            'details': e.messages
        }, "Error")), 400
    except Exception as e:
        logger.error(f"Error updating event {event_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify(get_marti_response({
            'error': 'Failed to update event',
            'details': str(e)
        }, "Error")), 500


@events_bp.route('/<int:event_id>', methods=['DELETE'])
def delete_event(event_id):
    """
    DELETE /Marti/api/events/<id>
    Delete event (admin only)
    
    Behavior:
    - If event is active (is_active=True): Performs soft delete by setting is_active=False
    - If event is inactive (is_active=False): Permanently deletes from database
    """
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify(get_marti_response({
                'error': 'Event not found',
                'event_id': event_id
            }, "Error")), 404
        
        event_name = event.name
        was_active = event.is_active
        
        if event.is_active:
            # Soft delete for active events
            event.is_active = False
            db.session.commit()
            
            logger.info(f"Event soft deleted (marked inactive): {event_name}")
            
            return jsonify(get_marti_response({
                'message': 'Event marked as inactive',
                'event_id': event_id,
                'permanent': False
            }, "EventDeleted")), 200
        else:
            # Permanent delete for inactive events
            db.session.delete(event)
            db.session.commit()
            
            logger.info(f"Event permanently deleted: {event_name}")
            
            return jsonify(get_marti_response({
                'message': 'Event permanently deleted',
                'event_id': event_id,
                'permanent': True
            }, "EventDeleted")), 200
        
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify(get_marti_response({
            'error': 'Failed to delete event',
            'details': str(e)
        }, "Error")), 500


@events_bp.route('/<int:event_id>/teams', methods=['GET'])
def get_event_teams(event_id):
    """
    GET /Marti/api/events/<id>/teams
    Get teams assigned to an event with participant counts
    """
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify(get_marti_response({
                'error': 'Event not found',
                'event_id': event_id
            }, "Error")), 404
        
        teams = event.get_teams()
        
        return jsonify(get_marti_response({
            'event_id': event_id,
            'teams': teams,
            'total': len(teams)
        })), 200
        
    except Exception as e:
        logger.error(f"Error getting teams for event {event_id}: {e}", exc_info=True)
        return jsonify(get_marti_response({
            'error': 'Failed to retrieve event teams',
            'details': str(e)
        }, "Error")), 500


@events_bp.route('/<int:event_id>/teams', methods=['POST'])
def assign_team_to_event(event_id):
    """
    POST /Marti/api/events/<id>/teams
    Assign a team to an event (admin only)
    
    Request body: TeamAssignmentSchema
    """
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify(get_marti_response({
                'error': 'Event not found',
                'event_id': event_id
            }, "Error")), 404
        
        # Validate input
        schema = TeamAssignmentSchema()
        data = schema.load(request.get_json())
        
        # Assign team to event
        event_team = event.add_team(
            team_id=data['team_id'],
            max_participants=data.get('max_participants')
        )
        
        logger.info(f"Team {data['team_id']} assigned to event {event.name}")
        
        return jsonify(get_marti_response({
            'event_team': event_team.to_dict(include_team=True),
            'message': 'Team assigned to event successfully'
        }, "TeamAssigned")), 201
        
    except ValidationError as e:
        return jsonify(get_marti_response({
            'error': 'Validation error',
            'details': e.messages
        }, "Error")), 400
    except Exception as e:
        logger.error(f"Error assigning team to event {event_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify(get_marti_response({
            'error': 'Failed to assign team to event',
            'details': str(e)
        }, "Error")), 500


@events_bp.route('/<int:event_id>/teams/<int:team_id>', methods=['DELETE'])
def remove_team_from_event(event_id, team_id):
    """
    DELETE /Marti/api/events/<id>/teams/<team_id>
    Remove a team from an event (admin only)
    """
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify(get_marti_response({
                'error': 'Event not found',
                'event_id': event_id
            }, "Error")), 404
        
        # Remove team from event
        success = event.remove_team(team_id)
        
        if not success:
            return jsonify(get_marti_response({
                'error': 'Team not assigned to this event',
                'event_id': event_id,
                'team_id': team_id
            }, "Error")), 404
        
        logger.info(f"Team {team_id} removed from event {event.name}")
        
        return jsonify(get_marti_response({
            'message': 'Team removed from event successfully',
            'event_id': event_id,
            'team_id': team_id
        }, "TeamRemoved")), 200
        
    except Exception as e:
        logger.error(f"Error removing team {team_id} from event {event_id}: {e}", exc_info=True)
        db.session.rollback()
        return jsonify(get_marti_response({
            'error': 'Failed to remove team from event',
            'details': str(e)
        }, "Error")), 500



@events_bp.route('/<int:event_id>/wifi-qr', methods=['GET'])
def get_event_wifi_qr(event_id):
    """
    GET /Marti/api/events/<id>/wifi-qr
    Get WiFi QR code string for event WiFi network
    
    Returns the WiFi QR code string in standard format that can be
    rendered as a QR code by the frontend.
    
    Response includes:
        - qr_string: WiFi QR code string in format WIFI:T:WPA;S:ssid;P:password;H:false;;
        - ssid: WiFi network SSID
        - security: Security type (WPA, WPA2, WEP, or nopass)
    """
    try:
        event = Event.query.get(event_id)
        
        if not event:
            return jsonify(get_marti_response({
                'error': 'Event not found',
                'event_id': event_id
            }, "Error")), 404
        
        # Check if event has WiFi configuration
        if not event.wifi_ssid or not event.wifi_password:
            return jsonify(get_marti_response({
                'error': 'Event does not have WiFi configuration',
                'event_id': event_id,
                'message': 'WiFi SSID and password must be configured for this event'
            }, "Error")), 400
        
        # Validate WiFi credentials
        is_valid, error_message = validate_wifi_credentials(
            event.wifi_ssid,
            event.wifi_password,
            security='WPA'
        )
        
        if not is_valid:
            logger.error(f"Invalid WiFi credentials for event {event_id}: {error_message}")
            return jsonify(get_marti_response({
                'error': 'Invalid WiFi configuration',
                'details': error_message
            }, "Error")), 400
        
        # Generate WiFi QR string
        try:
            qr_string = generate_wifi_qr_string(
                ssid=event.wifi_ssid,
                password=event.wifi_password,
                security='WPA'
            )
            
            logger.info(f"WiFi QR code generated for event {event.name}")
            
            return jsonify(get_marti_response({
                'qr_string': qr_string,
                'ssid': event.wifi_ssid,
                'security': 'WPA',
                'event_id': event_id,
                'event_name': event.name
            }, "WiFiQRCode")), 200
            
        except ValueError as e:
            logger.error(f"Error generating WiFi QR for event {event_id}: {e}")
            return jsonify(get_marti_response({
                'error': 'Failed to generate WiFi QR code',
                'details': str(e)
            }, "Error")), 400
        
    except Exception as e:
        logger.error(f"Error getting WiFi QR for event {event_id}: {e}", exc_info=True)
        return jsonify(get_marti_response({
            'error': 'Failed to retrieve WiFi QR code',
            'details': str(e)
        }, "Error")), 500
