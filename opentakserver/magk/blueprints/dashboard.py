#!/usr/bin/env python3
"""
Dashboard API Module
Provides real dashboard statistics from the database
"""

from flask import Blueprint, jsonify, request
import logging
import psycopg2
from datetime import datetime, timedelta
from opentakserver.magk.services.database import get_database_connection

# Create blueprint for dashboard API
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

def get_db_connection():
    """Get database connection"""
    return get_database_connection()

@dashboard_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Initialize stats
        stats = {
            'totalUsers': 0,
            'totalTeams': 0,
            'activeTeams': 0,
            'recentRegistrations': 0,
            'systemHealth': 'healthy'
        }
        
        # Get user statistics
        try:
            # Try to get users from common table names
            user_tables = ['users', 'user', 'tak_users', 'certificates']
            user_count = 0
            recent_count = 0
            
            for table in user_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    user_count = cursor.fetchone()[0]
                    
                    # Try to get recent registrations (last 7 days)
                    try:
                        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE created_at > ? OR date_created > ? OR timestamp > ?", 
                                     (week_ago, week_ago, week_ago))
                        recent_count = cursor.fetchone()[0]
                    except:
                        recent_count = 0
                    
                    break  # Found a working table
                except sqlite3.OperationalError:
                    continue  # Try next table
            
            stats['totalUsers'] = user_count
            stats['recentRegistrations'] = recent_count
            
        except Exception as e:
            logging.warning(f"Could not get user stats: {e}")
        
        # Get team/group statistics
        try:
            # Try to get teams from common table names
            team_tables = ['teams', 'groups', 'tak_groups', 'user_groups']
            team_count = 0
            active_count = 0
            
            for table in team_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    team_count = cursor.fetchone()[0]
                    
                    # Try to get active teams
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE active = 1 OR status = 'active'")
                        active_count = cursor.fetchone()[0]
                    except:
                        active_count = team_count  # Assume all are active if no status column
                    
                    break  # Found a working table
                except sqlite3.OperationalError:
                    continue  # Try next table
            
            stats['totalTeams'] = team_count
            stats['activeTeams'] = active_count
            
        except Exception as e:
            logging.warning(f"Could not get team stats: {e}")
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': 'Dashboard statistics retrieved successfully'
        })
        
    except Exception as e:
        logging.error(f"Failed to get dashboard stats: {e}")
        return jsonify({
            'success': False,
            'data': {
                'totalUsers': 0,
                'totalTeams': 0,
                'activeTeams': 0,
                'recentRegistrations': 0,
                'systemHealth': 'error'
            },
            'message': f'Failed to retrieve dashboard statistics: {str(e)}'
        }), 500

@dashboard_bp.route('/users', methods=['GET'])
def get_user_stats():
    """Get detailed user statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        stats = {
            'total': 0,
            'active': 0,
            'recent': 0,
            'admins': 0
        }
        
        # Try different user table names
        user_tables = ['users', 'user', 'tak_users', 'certificates']
        
        for table in user_tables:
            try:
                # Get total users
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats['total'] = cursor.fetchone()[0]
                
                # Get active users (try different column names)
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE active = 1")
                    stats['active'] = cursor.fetchone()[0]
                except:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE status = 'active'")
                        stats['active'] = cursor.fetchone()[0]
                    except:
                        stats['active'] = stats['total']  # Assume all active if no status column
                
                # Get recent users (last 7 days)
                try:
                    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE created_at > ?", (week_ago,))
                    stats['recent'] = cursor.fetchone()[0]
                except:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE date_created > ?", (week_ago,))
                        stats['recent'] = cursor.fetchone()[0]
                    except:
                        stats['recent'] = 0
                
                # Get admin users
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE is_admin = 1")
                    stats['admins'] = cursor.fetchone()[0]
                except:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE role = 'admin'")
                        stats['admins'] = cursor.fetchone()[0]
                    except:
                        stats['admins'] = 0
                
                break  # Found a working table
                
            except sqlite3.OperationalError:
                continue  # Try next table
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': 'User statistics retrieved successfully'
        })
        
    except Exception as e:
        logging.error(f"Failed to get user stats: {e}")
        return jsonify({
            'success': False,
            'data': {'total': 0, 'active': 0, 'recent': 0, 'admins': 0},
            'message': f'Failed to retrieve user statistics: {str(e)}'
        }), 500

@dashboard_bp.route('/teams', methods=['GET'])
def get_team_stats():
    """Get detailed team statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        stats = {
            'total': 0,
            'active': 0
        }
        
        # Try different team table names
        team_tables = ['teams', 'groups', 'tak_groups', 'user_groups']
        
        for table in team_tables:
            try:
                # Get total teams
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats['total'] = cursor.fetchone()[0]
                
                # Get active teams
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE active = 1")
                    stats['active'] = cursor.fetchone()[0]
                except:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE status = 'active'")
                        stats['active'] = cursor.fetchone()[0]
                    except:
                        stats['active'] = stats['total']  # Assume all active if no status column
                
                break  # Found a working table
                
            except sqlite3.OperationalError:
                continue  # Try next table
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': stats,
            'message': 'Team statistics retrieved successfully'
        })
        
    except Exception as e:
        logging.error(f"Failed to get team stats: {e}")
        return jsonify({
            'success': False,
            'data': {'total': 0, 'active': 0},
            'message': f'Failed to retrieve team statistics: {str(e)}'
        }), 500

@dashboard_bp.route('/health', methods=['GET'])
def get_system_health():
    """Get system health status"""
    try:
        # Check database connectivity
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
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