#!/usr/bin/env python3
"""
Marti API Authentication Endpoints
Provides authentication services following Marti API patterns
Replaces Flask-Security endpoints with Marti-compatible authentication
"""

from flask import Blueprint, jsonify, request, session
from flask_security import login_user, logout_user, current_user, auth_required
from flask_security.utils import verify_password
import logging
import uuid
from datetime import datetime, timezone

# Create blueprint following Marti API pattern
marti_auth_bp = Blueprint('marti_auth', __name__, url_prefix='/Marti/api/auth')

logger = logging.getLogger(__name__)

@marti_auth_bp.route('/login', methods=['POST'])
def marti_login():
    """
    Authenticate user using Marti API format
    Follows Marti API pattern: /Marti/api/auth/login
    """
    print("=== MARTI AUTH LOGIN CALLED ===", flush=True)
    try:
        data = request.get_json()
        print(f"Login data received: {data}", flush=True)
        
        print("About to extract username/password", flush=True)
        if not data:
            # Support form data for compatibility
            username = request.form.get('username')
            password = request.form.get('password')
        else:
            username = data.get('username')
            password = data.get('password')
        
        logger.info(f"Marti Auth: Login attempt for user {username}")
        
        if not username or not password:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Username and password are required"},
                "nodeId": "opentakserver-auth"
            }), 400
        
        # Find user using Flask-Security datastore
        from flask import current_app
        user_datastore = current_app.security.datastore
        user = user_datastore.find_user(username=username)
        
        print(f"User lookup result: {user}", flush=True)
        if user:
            print(f"User found: {user.username}, active: {user.active}", flush=True)
        else:
            print(f"User NOT found for username: {username}", flush=True)
        
        # Verify password using Flask-Security's verify_password
        password_valid = False
        if user:
            logger.info(f"Marti Auth: Found user {username}, checking password")
            
            try:
                print(f"Verifying password for user {username}", flush=True)
                print(f"Password hash starts with: {user.password[:50]}", flush=True)
                
                # Use Flask-Security's verify_password (imported at top) for consistency
                password_valid = verify_password(password, user.password)
                print(f"verify_password result: {password_valid}", flush=True)
                logger.info(f"Marti Auth: Password verification result: {password_valid}")
            except Exception as e:
                print(f"verify_password failed: {e}", flush=True)
                logger.error(f"Marti Auth: Password verification error: {e}")
                # Fallback to passlib directly
                try:
                    from passlib.context import CryptContext
                    pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
                    password_valid = pwd_context.verify(password, user.password)
                    print(f"Passlib verification result: {password_valid}", flush=True)
                    logger.info(f"Marti Auth: Passlib verification result: {password_valid}")
                except Exception as e2:
                    print(f"Passlib also failed: {e2}", flush=True)
                    logger.error(f"Marti Auth: Passlib verification also failed: {e2}")
                    password_valid = False
        else:
            logger.warning(f"Marti Auth: User {username} not found in datastore")
        
        if not user or not password_valid:
            logger.warning(f"Marti Auth: Failed login attempt for {username}")
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Invalid credentials"},
                "nodeId": "opentakserver-auth"
            }), 401
        
        if not user.active:
            logger.warning(f"Marti Auth: Login attempt for inactive user {username}")
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Account is not active"},
                "nodeId": "opentakserver-auth"
            }), 401
        
        # Login user (creates session)
        login_user(user, remember=True)
        
        # Generate session token for API compatibility
        session_token = str(uuid.uuid4())
        session['api_token'] = session_token
        
        # Log successful login activity
        try:
            from opentakserver.magk.models.activity_log import ActivityLog
            ActivityLog.log_activity(
                activity_type='user_login',
                user_id=user.id,
                description=f'User {username} logged in successfully',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                request_method=request.method,
                request_path=request.path,
                status_code=200,
                session_id=session_token,
                success=True
            )
        except Exception as e:
            logger.error(f"Failed to log login activity: {e}")
        
        # Prepare user data in Marti format
        user_roles = [role.name for role in user.roles]
        is_admin = 'administrator' in user_roles or 'admin' in user_roles
        
        user_data = {
            "uid": str(user.id),
            "username": user.username,
            "email": user.email,
            "active": user.active,
            "roles": [{"name": role.name} for role in user.roles],
            "is_admin": is_admin,
            "token": session_token,
            "authenticated": True,
            "loginTime": datetime.now(timezone.utc).isoformat()
        }
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.auth.User",
            "data": user_data,
            "nodeId": "opentakserver-auth"
        }
        
        logger.info(f"Marti Auth: Successful login for {username}")
        return jsonify(response), 200
        
    except Exception as e:
        print(f"=== EXCEPTION IN LOGIN: {e} ===", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        logger.error(f"Marti Auth: Login error: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Authentication failed: {str(e)}"},
            "nodeId": "opentakserver-auth"
        }), 500

@marti_auth_bp.route('/logout', methods=['POST'])
def marti_logout():
    """
    Logout user using Marti API format
    Follows Marti API pattern: /Marti/api/auth/logout
    """
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        username = current_user.username if current_user.is_authenticated else 'anonymous'
        
        logger.info(f"Marti Auth: Logout request for user {username}")
        
        # Log logout activity before clearing session
        if user_id:
            try:
                from opentakserver.magk.models.activity_log import ActivityLog
                ActivityLog.log_activity(
                    activity_type='user_logout',
                    user_id=user_id,
                    description=f'User {username} logged out',
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    request_method=request.method,
                    request_path=request.path,
                    status_code=200,
                    success=True
                )
            except Exception as e:
                logger.error(f"Failed to log logout activity: {e}")
        
        # Clear session
        session.clear()
        
        # Logout user
        logout_user()
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.auth.LogoutResponse",
            "data": {
                "message": "Logout successful",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "nodeId": "opentakserver-auth"
        }
        
        logger.info("Marti Auth: Logout successful")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Auth: Logout error: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Logout failed: {str(e)}"},
            "nodeId": "opentakserver-auth"
        }), 500

@marti_auth_bp.route('/me', methods=['GET'])
@auth_required()
def marti_me():
    """
    Get current user information using Marti API format
    Follows Marti API pattern: /Marti/api/auth/me
    """
    try:
        logger.info(f"Marti Auth: User info request for {current_user.username}")
        
        # Prepare user data in Marti format
        user_roles = [role.name for role in current_user.roles]
        is_admin = 'administrator' in user_roles or 'admin' in user_roles
        
        user_data = {
            "uid": str(current_user.id),
            "username": current_user.username,
            "email": current_user.email,
            "active": current_user.active,
            "roles": [{"name": role.name} for role in current_user.roles],
            "is_admin": is_admin,
            "token": session.get('api_token'),
            "authenticated": True,
            "lastActivity": datetime.now(timezone.utc).isoformat()
        }
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.auth.User",
            "data": user_data,
            "nodeId": "opentakserver-auth"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Auth: User info error: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to get user info: {str(e)}"},
            "nodeId": "opentakserver-auth"
        }), 500

@marti_auth_bp.route('/status', methods=['GET'])
def marti_auth_status():
    """
    Check authentication status using Marti API format
    Follows Marti API pattern: /Marti/api/auth/status
    """
    try:
        if current_user.is_authenticated:
            user_roles = [role.name for role in current_user.roles]
            is_admin = 'administrator' in user_roles or 'admin' in user_roles
            
            status_data = {
                "authenticated": True,
                "username": current_user.username,
                "is_admin": is_admin,
                "token": session.get('api_token'),
                "sessionActive": True
            }
        else:
            status_data = {
                "authenticated": False,
                "sessionActive": False
            }
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.auth.Status",
            "data": status_data,
            "nodeId": "opentakserver-auth"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Auth: Status check error: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to check auth status: {str(e)}"},
            "nodeId": "opentakserver-auth"
        }), 500

@marti_auth_bp.route('/csrf-token', methods=['GET'])
def marti_csrf_token():
    """
    Get CSRF token using Marti API format
    Follows Marti API pattern: /Marti/api/auth/csrf-token
    """
    try:
        from flask_wtf.csrf import generate_csrf
        
        csrf_token = generate_csrf()
        
        # Marti API response format
        response = {
            "version": "3",
            "type": "com.bbn.marti.remote.auth.CSRFToken",
            "data": {
                "csrf_token": csrf_token,
                "expires": "24h",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "nodeId": "opentakserver-auth"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Marti Auth: CSRF token error: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to generate CSRF token: {str(e)}"},
            "nodeId": "opentakserver-auth"
        }), 500

@marti_auth_bp.route('/health', methods=['GET'])
def marti_auth_health():
    """
    Health check for authentication system
    Follows Marti API pattern: /Marti/api/auth/health
    """
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.health.Status",
        "data": {
            "status": "healthy",
            "service": "marti-auth",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "nodeId": "opentakserver-auth"
    }), 200

# Error handlers following Marti API pattern
@marti_auth_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.UnauthorizedException",
        "data": {"message": "Authentication required"},
        "nodeId": "opentakserver-auth"
    }), 401

@marti_auth_bp.errorhandler(403)
def forbidden(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.ForbiddenException",
        "data": {"message": "Access forbidden"},
        "nodeId": "opentakserver-auth"
    }), 403

@marti_auth_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.NotFoundException",
        "data": {"message": "Authentication endpoint not found"},
        "nodeId": "opentakserver-auth"
    }), 404

@marti_auth_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.MethodNotAllowedException",
        "data": {"message": "Method not allowed"},
        "nodeId": "opentakserver-auth"
    }), 405

@marti_auth_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.exception.TakException",
        "data": {"message": "Internal server error"},
        "nodeId": "opentakserver-auth"
    }), 500