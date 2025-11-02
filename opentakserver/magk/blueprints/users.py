#!/usr/bin/env python3
"""
Marti API User Management Endpoints
Provides user management services following Marti API patterns
Integrates with existing Flask-Security user system
"""

from flask import Blueprint, jsonify, request
from flask_security import auth_required, current_user, roles_required
import logging
from datetime import datetime, timezone

# Create blueprint following Marti API pattern
marti_user_bp = Blueprint('marti_user', __name__, url_prefix='/Marti/api')

logger = logging.getLogger(__name__)

@marti_user_bp.route('/users', methods=['GET'])
@marti_user_bp.route('/auth/users', methods=['GET'])  # Alias for compatibility
def marti_get_users():
    """
    Get all users using Marti API format
    Follows Marti API pattern: /Marti/api/users
    """
    try:
        logger.info("Marti User API: Getting all users")
        
        # Get users from Flask-Security datastore
        from flask import current_app
        user_datastore = current_app.security.datastore
        
        # Get all users
        users = user_datastore.user_model.query.all()
        
        # Format users data in Marti format
        users_data = []
        for user in users:
            user_roles = [role.name for role in user.roles]
            is_admin = 'administrator' in user_roles or 'admin' in user_roles
            
            user_data = {
                "uid": str(user.id),
                "username": user.username,
                "email": user.email,
                "active": user.active,
                "roles": [{"name": role.name} for role in user.roles],
                "is_admin": is_admin,
                "created_at": user.confirmed_at.isoformat() if hasattr(user, 'confirmed_at') and user.confirmed_at else None,
                "last_login": user.last_login_at.isoformat() if hasattr(user, 'last_login_at') and user.last_login_at else None
            }
            users_data.append(user_data)
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.users.UserList",
            "data": users_data,
            "nodeId": "opentakserver-user-api"
        }
        
        logger.info(f"Marti User API: Returning {len(users_data)} users")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti User API: Error getting users: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve users: {str(e)}"},
            "nodeId": "opentakserver-user-api"
        }), 500

@marti_user_bp.route('/users/stats', methods=['GET'])
def marti_get_user_stats():
    """
    Get user statistics using Marti API format
    Follows Marti API pattern: /Marti/api/users/stats
    """
    try:
        logger.info("Marti User API: Getting user statistics")
        
        # Get users from Flask-Security datastore
        from flask import current_app
        user_datastore = current_app.security.datastore
        
        # Get all users
        users = user_datastore.user_model.query.all()
        
        # Calculate statistics
        total_users = len(users)
        active_users = len([u for u in users if u.active])
        inactive_users = total_users - active_users
        
        # Count admins
        admin_users = 0
        for user in users:
            user_roles = [role.name for role in user.roles]
            if 'administrator' in user_roles or 'admin' in user_roles:
                admin_users += 1
        
        # Count recent users (last 7 days)
        from datetime import timedelta
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_users = 0
        for user in users:
            if hasattr(user, 'confirmed_at') and user.confirmed_at and user.confirmed_at > week_ago:
                recent_users += 1
        
        # Count by role
        role_counts = {}
        for user in users:
            for role in user.roles:
                role_counts[role.name] = role_counts.get(role.name, 0) + 1
        
        stats_data = {
            "total": total_users,
            "active": active_users,
            "inactive": inactive_users,
            "admins": admin_users,
            "recent": recent_users,
            "byRole": role_counts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.users.UserStats",
            "data": stats_data,
            "nodeId": "opentakserver-user-api"
        }
        
        logger.info(f"Marti User API: Returning user stats - Total: {total_users}, Active: {active_users}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti User API: Error getting user stats: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve user statistics: {str(e)}"},
            "nodeId": "opentakserver-user-api"
        }), 500

@marti_user_bp.route('/users/<user_id>', methods=['GET'])
def marti_get_user(user_id):
    """
    Get a specific user by ID using Marti API format
    Follows Marti API pattern: /Marti/api/users/{id}
    """
    try:
        logger.info(f"Marti User API: Getting user {user_id}")
        
        # Get user from Flask-Security datastore
        from flask import current_app
        user_datastore = current_app.security.datastore
        
        # Find user by ID
        user = user_datastore.user_model.query.get(user_id)
        
        if not user:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.NotFoundException",
                "data": {"message": f"User {user_id} not found"},
                "nodeId": "opentakserver-user-api"
            }), 404
        
        # Format user data in Marti format
        user_roles = [role.name for role in user.roles]
        is_admin = 'administrator' in user_roles or 'admin' in user_roles
        
        user_data = {
            "uid": str(user.id),
            "username": user.username,
            "email": user.email,
            "active": user.active,
            "roles": [{"name": role.name} for role in user.roles],
            "is_admin": is_admin,
            "created_at": user.confirmed_at.isoformat() if hasattr(user, 'confirmed_at') and user.confirmed_at else None,
            "last_login": user.last_login_at.isoformat() if hasattr(user, 'last_login_at') and user.last_login_at else None
        }
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.users.User",
            "data": user_data,
            "nodeId": "opentakserver-user-api"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti User API: Error getting user {user_id}: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to retrieve user: {str(e)}"},
            "nodeId": "opentakserver-user-api"
        }), 500

@marti_user_bp.route('/users/<user_id>', methods=['PUT'])
def marti_update_user(user_id):
    """
    Update a user using Marti API format
    Follows Marti API pattern: /Marti/api/users/{id}
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Request body is required"},
                "nodeId": "opentakserver-user-api"
            }), 400
        
        logger.info(f"Marti User API: Updating user {user_id}")
        
        # Get user from Flask-Security datastore
        from flask import current_app
        user_datastore = current_app.security.datastore
        
        # Find user by ID
        user = user_datastore.user_model.query.get(user_id)
        
        if not user:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.NotFoundException",
                "data": {"message": f"User {user_id} not found"},
                "nodeId": "opentakserver-user-api"
            }), 404
        
        # Update user fields
        if 'username' in data and data['username'] != user.username:
            # Check if username already exists
            existing_user = user_datastore.find_user(username=data['username'])
            if existing_user and existing_user.id != user.id:
                return jsonify({
                    "version": "3",
                    "type": "com.bbn.marti.remote.exception.TakException",
                    "data": {"message": "Username already exists"},
                    "nodeId": "opentakserver-user-api"
                }), 409
            user.username = data['username']
        
        if 'email' in data and data['email'] != user.email:
            # Check if email already exists
            existing_email = user_datastore.find_user(email=data['email'])
            if existing_email and existing_email.id != user.id:
                return jsonify({
                    "version": "3",
                    "type": "com.bbn.marti.remote.exception.TakException",
                    "data": {"message": "Email already exists"},
                    "nodeId": "opentakserver-user-api"
                }), 409
            user.email = data['email']
        
        if 'active' in data:
            user.active = data['active']
        
        if 'password' in data and data['password']:
            user.password = data['password']
        
        # Update roles if specified
        if 'roles' in data:
            # Remove all current roles
            for role in user.roles:
                user_datastore.remove_role_from_user(user, role)
            
            # Add new roles
            for role_name in data['roles']:
                role = user_datastore.find_role(role_name)
                if role:
                    user_datastore.add_role_to_user(user, role)
        
        # Commit changes
        user_datastore.commit()
        
        # Format response
        user_roles = [role.name for role in user.roles]
        is_admin = 'administrator' in user_roles or 'admin' in user_roles
        
        user_data = {
            "uid": str(user.id),
            "username": user.username,
            "email": user.email,
            "active": user.active,
            "roles": [{"name": role.name} for role in user.roles],
            "is_admin": is_admin,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.users.User",
            "data": user_data,
            "nodeId": "opentakserver-user-api"
        }
        
        logger.info(f"Marti User API: User {user_id} updated successfully")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti User API: Error updating user {user_id}: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to update user: {str(e)}"},
            "nodeId": "opentakserver-user-api"
        }), 500

@marti_user_bp.route('/users/<user_id>', methods=['DELETE'])
def marti_delete_user(user_id):
    """
    Delete a user using Marti API format
    Follows Marti API pattern: /Marti/api/users/{id}
    """
    try:
        logger.info(f"Marti User API: Deleting user {user_id}")
        
        # Get user from Flask-Security datastore
        from flask import current_app
        user_datastore = current_app.security.datastore
        
        # Find user by ID
        user = user_datastore.user_model.query.get(user_id)
        
        if not user:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.NotFoundException",
                "data": {"message": f"User {user_id} not found"},
                "nodeId": "opentakserver-user-api"
            }), 404
        
        # Prevent deletion of current user
        if current_user.id == user.id:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Cannot delete your own account"},
                "nodeId": "opentakserver-user-api"
            }), 400
        
        # Delete user
        user_datastore.delete_user(user)
        user_datastore.commit()
        
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.users.UserDeleted",
            "data": {"message": f"User {user_id} deleted successfully"},
            "nodeId": "opentakserver-user-api"
        }
        
        logger.info(f"Marti User API: User {user_id} deleted successfully")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti User API: Error deleting user {user_id}: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to delete user: {str(e)}"},
            "nodeId": "opentakserver-user-api"
        }), 500

@marti_user_bp.route('/roles', methods=['GET'])
def marti_get_roles():
    """
    Get available roles for user management
    Follows Marti API pattern: /Marti/api/roles
    """
    try:
        from flask import current_app
        
        # Get all roles from Flask-Security
        roles = current_app.security.datastore.role_model.query.all()
        
        # Format roles for Marti API response
        roles_data = []
        for role in roles:
            roles_data.append({
                "id": role.id,
                "name": role.name,
                "description": role.description or f"Role: {role.name}",
                "permissions": list(role.permissions) if hasattr(role, 'permissions') else []
            })
        
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.auth.Role",
            "data": roles_data,
            "nodeId": "opentakserver-users"
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting roles: {e}", exc_info=True)
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to get roles: {str(e)}"},
            "nodeId": "opentakserver-users"
        }), 500

@marti_user_bp.route('/users', methods=['POST'])
def marti_create_user():
    """
    Create a new user using Marti API format
    Follows Marti API pattern: /Marti/api/users
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Request body is required"},
                "nodeId": "opentakserver-user-api"
            }), 400
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Username, email, and password are required"},
                "nodeId": "opentakserver-user-api"
            }), 400
        
        logger.info(f"Marti User API: Creating user {username}")
        
        # Create user using Flask-Security datastore
        from flask import current_app
        user_datastore = current_app.security.datastore
        
        # Check if user already exists
        existing_user = user_datastore.find_user(username=username)
        if existing_user:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Username already exists"},
                "nodeId": "opentakserver-user-api"
            }), 409
        
        existing_email = user_datastore.find_user(email=email)
        if existing_email:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Email already exists"},
                "nodeId": "opentakserver-user-api"
            }), 409
        
        # Create user
        user = user_datastore.create_user(
            username=username,
            email=email,
            password=password,
            active=data.get('active', True)
        )
        
        # Add roles if specified
        roles = data.get('roles', [])
        for role_name in roles:
            role = user_datastore.find_role(role_name)
            if role:
                user_datastore.add_role_to_user(user, role)
        
        # Commit changes
        user_datastore.commit()
        
        # Format response
        user_roles = [role.name for role in user.roles]
        is_admin = 'administrator' in user_roles or 'admin' in user_roles
        
        user_data = {
            "uid": str(user.id),
            "username": user.username,
            "email": user.email,
            "active": user.active,
            "roles": [{"name": role.name} for role in user.roles],
            "is_admin": is_admin,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.users.User",
            "data": user_data,
            "nodeId": "opentakserver-user-api"
        }
        
        logger.info(f"Marti User API: User {username} created successfully")
        return jsonify(response), 201
        
    except Exception as e:
        logger.error(f"Marti User API: Error creating user: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to create user: {str(e)}"},
            "nodeId": "opentakserver-user-api"
        }), 500

# Error handlers following Marti API pattern
@marti_user_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.UnauthorizedException",
        "data": {"message": "Authentication required"},
        "nodeId": "opentakserver-user-api"
    }), 401

@marti_user_bp.errorhandler(403)
def forbidden(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.ForbiddenException",
        "data": {"message": "Access forbidden"},
        "nodeId": "opentakserver-user-api"
    }), 403

@marti_user_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.NotFoundException",
        "data": {"message": "User endpoint not found"},
        "nodeId": "opentakserver-user-api"
    }), 404

@marti_user_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.TakException",
        "data": {"message": "Internal server error"},
        "nodeId": "opentakserver-user-api"
    }), 500