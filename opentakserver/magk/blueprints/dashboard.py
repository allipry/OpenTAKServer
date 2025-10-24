#!/usr/bin/env python3
"""
Dashboard API Module
Redirects to Marti API endpoints for dashboard statistics
"""

from flask import Blueprint, jsonify, request, redirect
from flask_security import auth_required, roles_required
import logging
from datetime import datetime

# Create blueprint for dashboard API
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@dashboard_bp.route('/stats', methods=['GET'])
@auth_required()
@roles_required('administrator')
def get_dashboard_stats():
    """
    Get dashboard statistics
    Uses Marti API user stats endpoint
    """
    try:
        from opentakserver.models.user import User
        from opentakserver.models.role import Role
        from datetime import datetime, timedelta, timezone
        
        # Get user statistics
        total_users = User.query.count()
        active_users = User.query.filter(User.active == True).count()
        
        # Get recent registrations (last 7 days)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_registrations = User.query.filter(User.confirmed_at >= week_ago).count() if hasattr(User, 'confirmed_at') else 0
        
        # Get admin count
        admin_role = Role.query.filter(Role.name == 'administrator').first()
        admin_count = 0
        if admin_role:
            admin_count = User.query.filter(User.roles.contains(admin_role)).count()
        
        stats = {
            'totalUsers': total_users,
            'activeUsers': active_users,
            'adminUsers': admin_count,
            'recentRegistrations': recent_registrations,
            'systemHealth': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': 'Dashboard statistics retrieved successfully'
        })
        
    except Exception as e:
        logging.error(f"Failed to get dashboard stats: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'data': {
                'totalUsers': 0,
                'activeUsers': 0,
                'adminUsers': 0,
                'recentRegistrations': 0,
                'systemHealth': 'error'
            },
            'message': f'Failed to retrieve dashboard statistics: {str(e)}'
        }), 500

@dashboard_bp.route('/users', methods=['GET'])
@auth_required()
@roles_required('administrator')
def get_user_stats():
    """
    Get detailed user statistics
    Redirects to Marti API /users/stats endpoint
    """
    try:
        from opentakserver.models.user import User
        from opentakserver.models.role import Role
        from opentakserver.extensions import db
        from sqlalchemy import func, and_
        from datetime import datetime, timedelta, timezone
        
        # Get statistics using SQLAlchemy (same as Marti API)
        total_users = User.query.count()
        active_users = User.query.filter(User.active == True).count()
        inactive_users = User.query.filter(User.active == False).count()
        
        # Get admin users
        admin_role = Role.query.filter(Role.name == 'administrator').first()
        admin_users = 0
        if admin_role:
            admin_users = User.query.filter(User.roles.contains(admin_role)).count()
        
        regular_users = total_users - admin_users
        
        # Get recent logins
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        recent_logins_24h = User.query.filter(User.last_login_at >= day_ago).count()
        recent_logins_7d = User.query.filter(User.last_login_at >= week_ago).count()
        
        stats = {
            'total': total_users,
            'active': active_users,
            'inactive': inactive_users,
            'admins': admin_users,
            'regular': regular_users,
            'recent_24h': recent_logins_24h,
            'recent_7d': recent_logins_7d,
            'timestamp': now.isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': 'User statistics retrieved successfully'
        })
        
    except Exception as e:
        logging.error(f"Failed to get user stats: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'data': {
                'total': 0,
                'active': 0,
                'inactive': 0,
                'admins': 0,
                'regular': 0,
                'recent_24h': 0,
                'recent_7d': 0
            },
            'message': f'Failed to retrieve user statistics: {str(e)}'
        }), 500

@dashboard_bp.route('/health', methods=['GET'])
def get_system_health():
    """Get system health status"""
    try:
        from opentakserver.extensions import db
        
        # Check database connectivity
        db.session.execute('SELECT 1')
        
        return jsonify({
            'success': True,
            'data': {
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now().isoformat()
            },
            'message': 'System health check passed'
        })
        
    except Exception as e:
        logging.error(f"Health check failed: {e}")
        return jsonify({
            'success': False,
            'data': {
                'status': 'unhealthy',
                'database': 'disconnected',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            },
            'message': 'System health check failed'
        }), 500

# Error handlers
@dashboard_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'data': None,
        'message': 'Endpoint not found'
    }), 404

@dashboard_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'data': None,
        'message': 'Internal server error'
    }), 500