"""
MAGK Teams Management API - Production-Ready CRUD Operations
Provides comprehensive team/group management with enterprise-grade features:
- Full CRUD operations with proper validation
- RFC 9457 Problem JSON error format
- Rate limiting and security
- Audit logging
- Pagination and search
- Bulk operations
- Team statistics
"""

import sys
sys.path.insert(0, '/app')

from flask import Blueprint, request, jsonify, g
from opentakserver.extensions import db
from opentakserver.models.Group import Group
from services.security_service import RateLimiter, InputValidator
from services.logging_service import LoggingService, EventType, LogLevel
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy import func, or_, and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
import logging
import re

logger = logging.getLogger(__name__)

# Initialize services
rate_limiter = RateLimiter()
input_validator = InputValidator()
logging_service = LoggingService()

# Create blueprint
teams_bp = Blueprint('magk_teams', __name__, url_prefix='/Marti/api/teams')

# Constants
MAX_TEAMS_PER_PAGE = 100
DEFAULT_PAGE_SIZE = 20
MAX_BULK_OPERATIONS = 50
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # seconds

# Validation patterns
TEAM_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s_.-]{1,100}$')


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_problem_response(title: str, status: int, detail: str = None, 
                           invalid_fields: List[Dict[str, str]] = None,
                           instance: str = None) -> Tuple[Dict[str, Any], int]:
    """
    Create RFC 9457 Problem JSON response
    
    Args:
        title: Short, human-readable summary
        status: HTTP status code
        detail: Human-readable explanation
        invalid_fields: List of field validation errors
        instance: URI identifying this occurrence
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    problem = {
        'version': '3',
        'type': f'com.bbn.marti.remote.exception.{title.replace(" ", "")}',
        'title': title,
        'status': status,
        'nodeId': 'opentakserver-teams',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    if detail:
        problem['detail'] = detail
    
    if invalid_fields:
        problem['invalid_fields'] = invalid_fields
    
    if instance:
        problem['instance'] = instance
    
    return jsonify(problem), status


def create_success_response(data: Any, message: str = None) -> Dict[str, Any]:
    """Create standardized success response in Marti format"""
    response = {
        'version': '3',
        'type': 'com.bbn.marti.remote.groups.Group',
        'data': data,
        'nodeId': 'opentakserver-teams'
    }
    
    if message:
        response['message'] = message
    
    return jsonify(response)


def validate_team_name(name: str) -> Tuple[bool, List[str]]:
    """Validate team name format and content"""
    errors = []
    
    if not name:
        errors.append('Team name is required')
        return False, errors
    
    if not isinstance(name, str):
        errors.append('Team name must be a string')
        return False, errors
    
    name = name.strip()
    
    if len(name) < 1:
        errors.append('Team name cannot be empty')
    elif len(name) > 100:
        errors.append('Team name cannot exceed 100 characters')
    
    if not TEAM_NAME_PATTERN.match(name):
        errors.append('Team name can only contain letters, numbers, spaces, hyphens, underscores, and periods')
    
    # Check for reserved names
    reserved_names = ['__ANON__', 'SYSTEM', 'ALL', 'NONE']
    if name.upper() in reserved_names:
        errors.append(f'Team name "{name}" is reserved and cannot be used')
    
    return len(errors) == 0, errors


def check_rate_limit() -> Optional[Tuple[Dict[str, Any], int]]:
    """Check rate limiting for current request"""
    client_ip = request.remote_addr
    is_allowed, current_count, reset_time = rate_limiter.is_allowed(
        client_ip, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW
    )
    
    if not is_allowed:
        reset_seconds = int(reset_time.total_seconds()) if reset_time else RATE_LIMIT_WINDOW
        
        logging_service.log_rate_limit_exceeded(
            ip_address=client_ip,
            endpoint=request.endpoint,
            limit=RATE_LIMIT_REQUESTS,
            window=RATE_LIMIT_WINDOW
        )
        
        return create_problem_response(
            title='Rate Limit Exceeded',
            status=429,
            detail=f'Too many requests. Please try again in {reset_seconds} seconds.',
            instance=request.path
        )
    
    return None


def serialize_team(team: Group) -> Dict[str, Any]:
    """Serialize team object to dictionary"""
    return {
        'id': team.id,
        'name': team.group_name,
        'type': team.group_type,
        'bitpos': team.bitpos,
        'created': team.created.isoformat() if team.created else None,
        'member_count': len(team.euds) if team.euds else 0
    }


# ============================================================================
# API ENDPOINTS
# ============================================================================

@teams_bp.route('', methods=['GET'])
def list_teams():
    """
    List all teams with pagination, search, and filtering
    
    Query Parameters:
        page (int): Page number (default: 1)
        page_size (int): Items per page (default: 20, max: 100)
        search (str): Search term for team name
        type (str): Filter by team type (SYSTEM, LDAP, IN)
        sort_by (str): Sort field (name, created, type)
        sort_order (str): Sort order (asc, desc)
    
    Returns:
        200: List of teams with pagination metadata
        429: Rate limit exceeded
        500: Internal server error
    """
    try:
        # Check rate limiting
        rate_limit_response = check_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        
        # Parse query parameters
        page = max(1, int(request.args.get('page', 1)))
        page_size = min(MAX_TEAMS_PER_PAGE, max(1, int(request.args.get('page_size', DEFAULT_PAGE_SIZE))))
        search = request.args.get('search', '').strip()
        team_type = request.args.get('type', '').strip().upper()
        sort_by = request.args.get('sort_by', 'name').lower()
        sort_order = request.args.get('sort_order', 'asc').lower()
        
        # Build query
        query = Group.query
        
        # Apply search filter
        if search:
            query = query.filter(Group.group_name.ilike(f'%{search}%'))
        
        # Apply type filter
        if team_type and team_type in ['SYSTEM', 'LDAP', 'IN']:
            query = query.filter(Group.group_type == team_type)
        
        # Apply sorting
        sort_column = {
            'name': Group.group_name,
            'created': Group.created,
            'type': Group.group_type,
            'bitpos': Group.bitpos
        }.get(sort_by, Group.group_name)
        
        if sort_order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        teams = query.offset(offset).limit(page_size).all()
        
        # Serialize teams
        teams_data = [serialize_team(team) for team in teams]
        
        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_prev = page > 1
        
        response_data = {
            'teams': teams_data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev
            }
        }
        
        return create_success_response(response_data)
        
    except ValueError as e:
        return create_problem_response(
            title='Invalid Request',
            status=400,
            detail=f'Invalid query parameter: {str(e)}'
        )
    except Exception as e:
        logger.error(f"Error listing teams: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='An unexpected error occurred while listing teams'
        )


@teams_bp.route('', methods=['POST'])
def create_team():
    """
    Create a new team
    
    Request Body:
        name (str, required): Team name (1-100 characters)
        type (str, optional): Team type (default: 'IN')
    
    Returns:
        201: Team created successfully
        400: Invalid request data
        409: Team already exists
        422: Validation error
        429: Rate limit exceeded
        500: Internal server error
    """
    try:
        # Check rate limiting
        rate_limit_response = check_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        
        # Parse request data
        data = request.get_json()
        if not data:
            return create_problem_response(
                title='Invalid Request',
                status=400,
                detail='Request body is required'
            )
        
        team_name = data.get('name', '').strip()
        team_type = data.get('type', 'IN').strip().upper()
        
        # Validate team name
        is_valid, errors = validate_team_name(team_name)
        if not is_valid:
            invalid_fields = [{'field': 'name', 'message': error} for error in errors]
            return create_problem_response(
                title='Validation Error',
                status=422,
                detail='Team name validation failed',
                invalid_fields=invalid_fields
            )
        
        # Validate team type
        if team_type not in ['IN', 'OUT', 'SYSTEM', 'LDAP']:
            return create_problem_response(
                title='Validation Error',
                status=422,
                detail='Invalid team type',
                invalid_fields=[{
                    'field': 'type',
                    'message': 'Team type must be one of: IN, OUT, SYSTEM, LDAP'
                }]
            )
        
        # Check if team already exists
        existing_team = Group.query.filter(
            func.lower(Group.group_name) == func.lower(team_name)
        ).first()
        
        if existing_team:
            return create_problem_response(
                title='Conflict',
                status=409,
                detail=f'Team "{team_name}" already exists'
            )
        
        # Find next available bitpos
        max_bitpos = db.session.query(func.max(Group.bitpos)).scalar() or 1
        next_bitpos = max_bitpos + 1
        
        # Create new team
        new_team = Group(
            group_name=team_name,
            created=datetime.utcnow(),
            group_type=team_type,
            bitpos=next_bitpos
        )
        
        db.session.add(new_team)
        db.session.commit()
        
        # Log team creation
        logging_service._create_log_entry(
            event_type=EventType.TEAM_CREATED,
            level=LogLevel.INFO,
            message=f'Team created: {team_name}',
            details={'team_id': new_team.id, 'team_name': team_name, 'team_type': team_type},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        logger.info(f"Team created: {team_name} (ID: {new_team.id})")
        
        return create_success_response(
            serialize_team(new_team),
            message=f'Team "{team_name}" created successfully'
        ), 201
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Database integrity error creating team: {e}")
        return create_problem_response(
            title='Conflict',
            status=409,
            detail='Team creation failed due to database constraint violation'
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating team: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='Database error occurred while creating team'
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error creating team: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='An unexpected error occurred while creating team'
        )


@teams_bp.route('/<int:team_id>', methods=['GET'])
def get_team(team_id: int):
    """
    Get team details by ID
    
    Path Parameters:
        team_id (int): Team ID
    
    Returns:
        200: Team details
        404: Team not found
        429: Rate limit exceeded
        500: Internal server error
    """
    try:
        # Check rate limiting
        rate_limit_response = check_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        
        team = Group.query.get(team_id)
        if not team:
            return create_problem_response(
                title='Not Found',
                status=404,
                detail=f'Team with ID {team_id} not found'
            )
        
        return create_success_response(serialize_team(team))
        
    except Exception as e:
        logger.error(f"Error getting team {team_id}: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='An unexpected error occurred while retrieving team'
        )


@teams_bp.route('/<int:team_id>', methods=['PUT'])
def update_team(team_id: int):
    """
    Update an existing team
    
    Path Parameters:
        team_id (int): Team ID
    
    Request Body:
        name (str, optional): New team name
        type (str, optional): New team type
    
    Returns:
        200: Team updated successfully
        400: Invalid request data
        404: Team not found
        409: Team name already exists
        422: Validation error
        429: Rate limit exceeded
        500: Internal server error
    """
    try:
        # Check rate limiting
        rate_limit_response = check_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        
        team = Group.query.get(team_id)
        if not team:
            return create_problem_response(
                title='Not Found',
                status=404,
                detail=f'Team with ID {team_id} not found'
            )
        
        # Don't allow updating system teams
        if team.group_type == 'SYSTEM':
            return create_problem_response(
                title='Forbidden',
                status=403,
                detail='System teams cannot be modified'
            )
        
        data = request.get_json()
        if not data:
            return create_problem_response(
                title='Invalid Request',
                status=400,
                detail='Request body is required'
            )
        
        updated_fields = []
        
        # Update team name if provided
        if 'name' in data:
            new_name = data['name'].strip()
            is_valid, errors = validate_team_name(new_name)
            if not is_valid:
                invalid_fields = [{'field': 'name', 'message': error} for error in errors]
                return create_problem_response(
                    title='Validation Error',
                    status=422,
                    detail='Team name validation failed',
                    invalid_fields=invalid_fields
                )
            
            # Check if new name conflicts with existing team
            if new_name.lower() != team.group_name.lower():
                existing = Group.query.filter(
                    func.lower(Group.group_name) == func.lower(new_name),
                    Group.id != team_id
                ).first()
                
                if existing:
                    return create_problem_response(
                        title='Conflict',
                        status=409,
                        detail=f'Team name "{new_name}" is already in use'
                    )
                
                team.group_name = new_name
                updated_fields.append('name')
        
        # Update team type if provided
        if 'type' in data:
            new_type = data['type'].strip().upper()
            if new_type not in ['IN', 'OUT', 'SYSTEM', 'LDAP']:
                return create_problem_response(
                    title='Validation Error',
                    status=422,
                    detail='Invalid team type',
                    invalid_fields=[{
                        'field': 'type',
                        'message': 'Team type must be one of: IN, OUT, SYSTEM, LDAP'
                    }]
                )
            
            team.group_type = new_type
            updated_fields.append('type')
        
        if not updated_fields:
            return create_problem_response(
                title='Invalid Request',
                status=400,
                detail='No valid fields provided for update'
            )
        
        db.session.commit()
        
        # Log team update
        logging_service._create_log_entry(
            event_type=EventType.TEAM_UPDATED,
            level=LogLevel.INFO,
            message=f'Team updated: {team.group_name}',
            details={'team_id': team_id, 'updated_fields': updated_fields},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        logger.info(f"Team updated: {team.group_name} (ID: {team_id})")
        
        return create_success_response(
            serialize_team(team),
            message=f'Team updated successfully'
        )
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Database integrity error updating team: {e}")
        return create_problem_response(
            title='Conflict',
            status=409,
            detail='Team update failed due to database constraint violation'
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating team: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='Database error occurred while updating team'
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error updating team: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='An unexpected error occurred while updating team'
        )


@teams_bp.route('/<int:team_id>', methods=['DELETE'])
def delete_team(team_id: int):
    """
    Delete a team
    
    Path Parameters:
        team_id (int): Team ID
    
    Query Parameters:
        force (bool): Force delete even if team has members (default: false)
    
    Returns:
        200: Team deleted successfully
        403: Cannot delete system team or team with members
        404: Team not found
        429: Rate limit exceeded
        500: Internal server error
    """
    try:
        # Check rate limiting
        rate_limit_response = check_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        
        team = Group.query.get(team_id)
        if not team:
            return create_problem_response(
                title='Not Found',
                status=404,
                detail=f'Team with ID {team_id} not found'
            )
        
        # Don't allow deleting system teams
        if team.group_type == 'SYSTEM':
            return create_problem_response(
                title='Forbidden',
                status=403,
                detail='System teams cannot be deleted'
            )
        
        # Check if team has members
        force = request.args.get('force', 'false').lower() == 'true'
        member_count = len(team.euds) if team.euds else 0
        
        if member_count > 0 and not force:
            return create_problem_response(
                title='Forbidden',
                status=403,
                detail=f'Team has {member_count} member(s). Use force=true to delete anyway.'
            )
        
        team_name = team.group_name
        
        db.session.delete(team)
        db.session.commit()
        
        # Log team deletion
        logging_service._create_log_entry(
            event_type=EventType.TEAM_DELETED,
            level=LogLevel.INFO,
            message=f'Team deleted: {team_name}',
            details={'team_id': team_id, 'team_name': team_name, 'forced': force},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        logger.info(f"Team deleted: {team_name} (ID: {team_id})")
        
        return create_success_response(
            {'deleted': True, 'team_id': team_id, 'team_name': team_name},
            message=f'Team "{team_name}" deleted successfully'
        )
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error deleting team: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='Database error occurred while deleting team'
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error deleting team: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='An unexpected error occurred while deleting team'
        )


@teams_bp.route('/bulk', methods=['POST'])
def bulk_create_teams():
    """
    Create multiple teams in a single request
    
    Request Body:
        teams (array): Array of team objects with 'name' and optional 'type'
    
    Returns:
        207: Multi-Status with results for each team
        400: Invalid request data
        429: Rate limit exceeded
    """
    try:
        # Check rate limiting
        rate_limit_response = check_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        
        data = request.get_json()
        if not data or 'teams' not in data:
            return create_problem_response(
                title='Invalid Request',
                status=400,
                detail='Request body must contain "teams" array'
            )
        
        teams_data = data['teams']
        if not isinstance(teams_data, list):
            return create_problem_response(
                title='Invalid Request',
                status=400,
                detail='"teams" must be an array'
            )
        
        if len(teams_data) > MAX_BULK_OPERATIONS:
            return create_problem_response(
                title='Invalid Request',
                status=400,
                detail=f'Maximum {MAX_BULK_OPERATIONS} teams allowed per bulk operation'
            )
        
        results = []
        successful_count = 0
        failed_count = 0
        
        for idx, team_data in enumerate(teams_data):
            try:
                team_name = team_data.get('name', '').strip()
                team_type = team_data.get('type', 'IN').strip().upper()
                
                # Validate team name
                is_valid, errors = validate_team_name(team_name)
                if not is_valid:
                    results.append({
                        'index': idx,
                        'name': team_name,
                        'status': 422,
                        'success': False,
                        'errors': errors
                    })
                    failed_count += 1
                    continue
                
                # Check if team exists
                existing = Group.query.filter(
                    func.lower(Group.group_name) == func.lower(team_name)
                ).first()
                
                if existing:
                    results.append({
                        'index': idx,
                        'name': team_name,
                        'status': 409,
                        'success': False,
                        'error': f'Team "{team_name}" already exists'
                    })
                    failed_count += 1
                    continue
                
                # Find next bitpos
                max_bitpos = db.session.query(func.max(Group.bitpos)).scalar() or 1
                next_bitpos = max_bitpos + 1
                
                # Create team
                new_team = Group(
                    group_name=team_name,
                    created=datetime.utcnow(),
                    group_type=team_type,
                    bitpos=next_bitpos
                )
                
                db.session.add(new_team)
                db.session.flush()  # Get ID without committing
                
                results.append({
                    'index': idx,
                    'name': team_name,
                    'status': 201,
                    'success': True,
                    'team': serialize_team(new_team)
                })
                successful_count += 1
                
            except Exception as e:
                logger.error(f"Error creating team in bulk operation: {e}")
                results.append({
                    'index': idx,
                    'name': team_data.get('name', 'unknown'),
                    'status': 500,
                    'success': False,
                    'error': 'Internal error occurred'
                })
                failed_count += 1
        
        # Commit all successful operations
        if successful_count > 0:
            db.session.commit()
            logger.info(f"Bulk team creation: {successful_count} successful, {failed_count} failed")
        else:
            db.session.rollback()
        
        response = {
            'version': '3',
            'type': 'com.bbn.marti.remote.groups.BulkOperationResult',
            'data': {
                'results': results,
                'summary': {
                    'total': len(teams_data),
                    'successful': successful_count,
                    'failed': failed_count
                }
            },
            'nodeId': 'opentakserver-teams'
        }
        
        return jsonify(response), 207
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error in bulk team creation: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='An unexpected error occurred during bulk operation'
        )


@teams_bp.route('/statistics', methods=['GET'])
def get_team_statistics():
    """
    Get team statistics and metrics
    
    Returns:
        200: Team statistics
        429: Rate limit exceeded
        500: Internal server error
    """
    try:
        # Check rate limiting
        rate_limit_response = check_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        
        # Get counts by type
        total_teams = Group.query.count()
        system_teams = Group.query.filter_by(group_type='SYSTEM').count()
        ldap_teams = Group.query.filter_by(group_type='LDAP').count()
        in_teams = Group.query.filter_by(group_type='IN').count()
        out_teams = Group.query.filter_by(group_type='OUT').count()
        
        # Get teams with most members
        teams_with_members = db.session.query(
            Group,
            func.count(Group.euds).label('member_count')
        ).outerjoin(Group.euds).group_by(Group.id).order_by(
            func.count(Group.euds).desc()
        ).limit(10).all()
        
        top_teams = [
            {
                'team': serialize_team(team),
                'member_count': count
            }
            for team, count in teams_with_members
        ]
        
        # Get recent teams
        recent_teams = Group.query.order_by(Group.created.desc()).limit(10).all()
        recent_teams_data = [serialize_team(team) for team in recent_teams]
        
        statistics = {
            'total_teams': total_teams,
            'by_type': {
                'SYSTEM': system_teams,
                'LDAP': ldap_teams,
                'IN': in_teams,
                'OUT': out_teams
            },
            'top_teams_by_members': top_teams,
            'recent_teams': recent_teams_data
        }
        
        return create_success_response(statistics)
        
    except Exception as e:
        logger.error(f"Error getting team statistics: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='An unexpected error occurred while retrieving statistics'
        )


@teams_bp.route('/search', methods=['GET'])
def search_teams():
    """
    Advanced team search with multiple criteria
    
    Query Parameters:
        q (str): Search query (searches name)
        type (str): Filter by team type
        min_members (int): Minimum member count
        max_members (int): Maximum member count
        created_after (str): ISO date - teams created after this date
        created_before (str): ISO date - teams created before this date
        limit (int): Maximum results (default: 50, max: 100)
    
    Returns:
        200: Search results
        400: Invalid query parameters
        429: Rate limit exceeded
        500: Internal server error
    """
    try:
        # Check rate limiting
        rate_limit_response = check_rate_limit()
        if rate_limit_response:
            return rate_limit_response
        
        # Parse query parameters
        search_query = request.args.get('q', '').strip()
        team_type = request.args.get('type', '').strip().upper()
        min_members = request.args.get('min_members', type=int)
        max_members = request.args.get('max_members', type=int)
        created_after = request.args.get('created_after')
        created_before = request.args.get('created_before')
        limit = min(100, max(1, int(request.args.get('limit', 50))))
        
        # Build query
        query = Group.query
        
        # Apply search filter
        if search_query:
            query = query.filter(Group.group_name.ilike(f'%{search_query}%'))
        
        # Apply type filter
        if team_type and team_type in ['SYSTEM', 'LDAP', 'IN', 'OUT']:
            query = query.filter(Group.group_type == team_type)
        
        # Apply date filters
        if created_after:
            try:
                after_date = datetime.fromisoformat(created_after.replace('Z', '+00:00'))
                query = query.filter(Group.created >= after_date)
            except ValueError:
                return create_problem_response(
                    title='Invalid Request',
                    status=400,
                    detail='Invalid created_after date format. Use ISO 8601 format.'
                )
        
        if created_before:
            try:
                before_date = datetime.fromisoformat(created_before.replace('Z', '+00:00'))
                query = query.filter(Group.created <= before_date)
            except ValueError:
                return create_problem_response(
                    title='Invalid Request',
                    status=400,
                    detail='Invalid created_before date format. Use ISO 8601 format.'
                )
        
        # Execute query
        teams = query.limit(limit).all()
        
        # Apply member count filters (post-query since it requires relationship data)
        if min_members is not None or max_members is not None:
            filtered_teams = []
            for team in teams:
                member_count = len(team.euds) if team.euds else 0
                if min_members is not None and member_count < min_members:
                    continue
                if max_members is not None and member_count > max_members:
                    continue
                filtered_teams.append(team)
            teams = filtered_teams
        
        # Serialize results
        results = [serialize_team(team) for team in teams]
        
        response_data = {
            'results': results,
            'count': len(results),
            'query': {
                'search': search_query,
                'type': team_type,
                'min_members': min_members,
                'max_members': max_members,
                'created_after': created_after,
                'created_before': created_before
            }
        }
        
        return create_success_response(response_data)
        
    except ValueError as e:
        return create_problem_response(
            title='Invalid Request',
            status=400,
            detail=f'Invalid query parameter: {str(e)}'
        )
    except Exception as e:
        logger.error(f"Error searching teams: {e}", exc_info=True)
        return create_problem_response(
            title='Internal Server Error',
            status=500,
            detail='An unexpected error occurred during search'
        )


# Health check endpoint
@teams_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for team management API"""
    try:
        # Test database connection
        db.session.execute(db.select(func.count()).select_from(Group)).scalar()
        
        return jsonify({
            'status': 'healthy',
            'service': 'team-management-api',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'team-management-api',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 503
