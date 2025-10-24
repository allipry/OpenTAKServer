#!/usr/bin/env python3
"""
Marti API Activity Feed Endpoints
Provides activity logging and feed services following Marti API patterns
Integrates with ActivityLog model and Flask-Security user system
"""

from flask import Blueprint, jsonify, request
from flask_security import auth_required, roles_required
import logging
from datetime import datetime, timezone

# Create blueprint following Marti API pattern
marti_activity_bp = Blueprint('marti_activity', __name__, url_prefix='/Marti/api')

logger = logging.getLogger(__name__)

@marti_activity_bp.route('/activity/recent', methods=['GET'])
@auth_required()
@roles_required('administrator')
def marti_get_recent_activity():
    """
    Get recent activity logs using Marti API format
    Follows Marti API pattern: /Marti/api/activity/recent
    
    Query Parameters:
        limit (int): Maximum number of activities to return (default: 50, max: 100)
        activity_type (str): Filter by activity type
        user_id (int): Filter by user ID
        success (bool): Filter by success status
    
    Returns:
        JSON response with recent activities in Marti API format
    """
    try:
        # Import ActivityLog model
        from opentakserver.magk.models.activity_log import ActivityLog
        
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)  # Max 100 activities
        activity_type = request.args.get('activity_type')
        user_id = request.args.get('user_id', type=int)
        success_filter = request.args.get('success')
        
        logger.info(f"Marti Activity API: Getting recent {limit} activities")
        
        # Build query
        query = ActivityLog.query
        
        # Apply filters
        if activity_type:
            query = query.filter(ActivityLog.activity_type == activity_type)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if success_filter is not None:
            success_bool = success_filter.lower() in ['true', '1', 'yes']
            query = query.filter(ActivityLog.success == success_bool)
        
        # Order by most recent first and limit
        activities = query.order_by(
            ActivityLog.created_at.desc()
        ).limit(limit).all()
        
        # Format activities data in Marti format
        activities_data = [activity.to_dict() for activity in activities]
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.activity.ActivityList",
            "data": activities_data,
            "nodeId": "opentakserver-activity-api"
        }
        
        logger.info(f"Marti Activity API: Returning {len(activities_data)} activities")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Activity API: Error getting activities: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve activities: {str(e)}"},
            "nodeId": "opentakserver-activity-api"
        }), 500

@marti_activity_bp.route('/activity/stats', methods=['GET'])
@auth_required()
@roles_required('administrator')
def marti_get_activity_stats():
    """
    Get activity statistics using Marti API format
    Follows Marti API pattern: /Marti/api/activity/stats
    
    Query Parameters:
        days (int): Number of days to include in statistics (default: 7, max: 30)
    
    Returns:
        JSON response with activity statistics in Marti API format
    """
    try:
        from opentakserver.magk.models.activity_log import ActivityLog
        
        # Get query parameters
        days = request.args.get('days', 7, type=int)
        days = min(max(days, 1), 30)  # Ensure days is between 1 and 30
        
        logger.info(f"Marti Activity API: Getting activity stats for {days} days")
        
        # Get activity summary using ActivityLog model
        activity_summary = ActivityLog.get_activity_summary(days=days)
        
        # Format summary data from the dictionary returned by get_activity_summary
        activity_types_list = []
        for activity_type, type_stats in activity_summary.get('activity_types', {}).items():
            activity_data = {
                "activity_type": activity_type,
                "count": type_stats['total'],
                "success_count": type_stats['successful'],
                "failure_count": type_stats['failed'],
                "success_rate": round((type_stats['successful'] / type_stats['total'] * 100), 2) if type_stats['total'] > 0 else 0
            }
            activity_types_list.append(activity_data)
        
        stats_data = {
            "time_period_days": activity_summary['time_period_days'],
            "start_date": activity_summary['start_date'],
            "end_date": activity_summary['end_date'],
            "activity_types": activity_types_list,
            "total_activities": activity_summary['total_activities'],
            "total_success": activity_summary['successful_activities'],
            "total_failures": activity_summary['failed_activities'],
            "overall_success_rate": round(activity_summary['success_rate'], 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.activity.ActivityStats",
            "data": stats_data,
            "nodeId": "opentakserver-activity-api"
        }
        
        logger.info(f"Marti Activity API: Returning activity stats - {stats_data['total_activities']} activities over {days} days")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Activity API: Error getting activity stats: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve activity statistics: {str(e)}"},
            "nodeId": "opentakserver-activity-api"
        }), 500

@marti_activity_bp.route('/activity/<int:activity_id>', methods=['GET'])
@auth_required()
@roles_required('administrator')
def marti_get_activity_details(activity_id):
    """
    Get detailed information about a specific activity
    Follows Marti API pattern: /Marti/api/activity/<id>
    
    Parameters:
        activity_id (int): ID of the activity to retrieve
    
    Returns:
        JSON response with activity details in Marti API format
    """
    try:
        from opentakserver.magk.models.activity_log import ActivityLog
        
        logger.info(f"Marti Activity API: Getting activity details for ID {activity_id}")
        
        # Query specific activity
        activity = ActivityLog.query.get(activity_id)
        
        if not activity:
            logger.warning(f"Marti Activity API: Activity {activity_id} not found")
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.NotFoundException",
                "data": {"message": f"Activity with ID {activity_id} not found"},
                "nodeId": "opentakserver-activity-api"
            }), 404
        
        # Format activity data with full details
        activity_data = activity.to_dict()
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.activity.ActivityDetails",
            "data": activity_data,
            "nodeId": "opentakserver-activity-api"
        }
        
        logger.info(f"Marti Activity API: Returning details for activity {activity_id}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Activity API: Error getting activity {activity_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve activity details: {str(e)}"},
            "nodeId": "opentakserver-activity-api"
        }), 500

@marti_activity_bp.route('/activity/types', methods=['GET'])
@auth_required()
@roles_required('administrator')
def marti_get_activity_types():
    """
    Get list of activity types with counts
    Follows Marti API pattern: /Marti/api/activity/types
    
    Returns:
        JSON response with activity type statistics
    """
    try:
        from opentakserver.magk.models.activity_log import ActivityLog
        from sqlalchemy import func
        
        logger.info("Marti Activity API: Getting activity types")
        
        # Query activity types with counts
        type_counts = ActivityLog.query.with_entities(
            ActivityLog.activity_type,
            func.count(ActivityLog.id).label('count')
        ).group_by(ActivityLog.activity_type).all()
        
        # Format data
        types_data = [
            {"type": type_name, "count": count}
            for type_name, count in type_counts
        ]
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.activity.ActivityTypes",
            "data": types_data,
            "nodeId": "opentakserver-activity-api"
        }
        
        logger.info(f"Marti Activity API: Returning {len(types_data)} activity types")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Activity API: Error getting activity types: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve activity types: {str(e)}"},
            "nodeId": "opentakserver-activity-api"
        }), 500

# Error handlers following Marti API pattern
@marti_activity_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.UnauthorizedException",
        "data": {"message": "Authentication required"},
        "nodeId": "opentakserver-activity-api"
    }), 401

@marti_activity_bp.errorhandler(403)
def forbidden(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.ForbiddenException",
        "data": {"message": "Access forbidden - Administrator role required"},
        "nodeId": "opentakserver-activity-api"
    }), 403

@marti_activity_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.NotFoundException",
        "data": {"message": "Activity endpoint not found"},
        "nodeId": "opentakserver-activity-api"
    }), 404

@marti_activity_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.TakException",
        "data": {"message": "Internal server error"},
        "nodeId": "opentakserver-activity-api"
    }), 500
