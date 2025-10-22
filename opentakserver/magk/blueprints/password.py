#!/usr/bin/env python3
"""
Password Management API
Provides password strength checking and reset functionality
"""

from flask import Blueprint, jsonify, request, current_app, url_for
from flask_security import auth_required, current_user, hash_password
import logging
import secrets
import uuid
from datetime import datetime, timezone, timedelta

# Create blueprint
password_bp = Blueprint('password', __name__, url_prefix='/Marti/api/password')

logger = logging.getLogger(__name__)

@password_bp.route('/strength', methods=['POST'])
def check_password_strength():
    """
    Check password strength without storing it
    POST /Marti/api/password/strength
    Body: {"password": "string"}
    """
    try:
        data = request.get_json()
        if not data or 'password' not in data:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Password is required"},
                "nodeId": "opentakserver-password"
            }), 400
        
        password = data['password']
        
        # Get password validator from app
        password_util = current_app.security.password_util
        
        # Check strength
        strength_info = password_util.get_password_strength(password)
        
        # Check validation errors
        errors, _ = password_util.validate(password, is_register=True)
        
        response_data = {
            "score": strength_info['score'],
            "strength": strength_info['strength'],
            "feedback": strength_info['feedback'],
            "valid": errors is None or len(errors) == 0,
            "errors": errors if errors else []
        }
        
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.password.Strength",
            "data": response_data,
            "nodeId": "opentakserver-password"
        }), 200
        
    except Exception as e:
        logger.error(f"Password strength check error: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": f"Failed to check password strength: {str(e)}"},
            "nodeId": "opentakserver-password"
        }), 500

@password_bp.route('/reset/request', methods=['POST'])
def request_password_reset():
    """
    Request a password reset email
    POST /Marti/api/password/reset/request
    Body: {"email": "user@example.com"}
    """
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Email is required"},
                "nodeId": "opentakserver-password"
            }), 400
        
        email = data['email']
        logger.info(f"Password reset requested for email: {email}")
        
        # Find user by email
        user_datastore = current_app.security.datastore
        user = user_datastore.find_user(email=email)
        
        if not user:
            # Don't reveal if user exists or not (security best practice)
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.password.ResetRequest",
                "data": {
                    "message": "If an account exists with this email, a password reset link has been sent",
                    "email": email
                },
                "nodeId": "opentakserver-password"
            }), 200
        
        if not user.active:
            logger.warning(f"Password reset requested for inactive user: {email}")
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.password.ResetRequest",
                "data": {
                    "message": "If an account exists with this email, a password reset link has been sent",
                    "email": email
                },
                "nodeId": "opentakserver-password"
            }), 200
        
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        
        # Store token in database (using registration_logs table temporarily)
        from opentakserver.magk.services.database import get_database_connection
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Calculate expiration (24 hours from now)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        
        # Store reset token
        import json as json_module
        registration_data_json = json_module.dumps({
            'type': 'password_reset',
            'email': email,
            'requested_at': datetime.now(timezone.utc).isoformat()
        })
        
        cursor.execute("""
            INSERT INTO registration_logs 
            (user_id, status, download_token, token_expires_at, registration_data, device_type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            user.id,
            'password_reset',
            reset_token,
            expires_at,
            registration_data_json,
            'other'
        ))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Generate reset URL
        reset_url = f"https://{request.host}/reset-password?token={reset_token}"
        
        print(f"=== PASSWORD RESET EMAIL ===", flush=True)
        print(f"Email: {user.email}", flush=True)
        print(f"Username: {user.username}", flush=True)
        print(f"Token: {reset_token}", flush=True)
        print(f"Reset URL: {reset_url}", flush=True)
        print(f"=== END ===", flush=True)
        
        # Send reset email
        try:
            from opentakserver.magk.services.email import email_service
            
            email_sent = email_service.send_password_reset_email(
                email=user.email,
                username=user.username,
                reset_url=reset_url,
                expires_hours=24
            )
            
            if email_sent:
                logger.info(f"Password reset email sent to: {email}")
                print(f"✓ Email sent successfully to {email}", flush=True)
            else:
                logger.error(f"Failed to send password reset email to: {email}")
                print(f"✗ Email failed to send to {email}", flush=True)
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            # Don't fail the request if email fails - token is still valid
        
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.password.ResetRequest",
            "data": {
                "message": "If an account exists with this email, a password reset link has been sent",
                "email": email,
                "expires_in_hours": 24
            },
            "nodeId": "opentakserver-password"
        }), 200
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"=== PASSWORD RESET ERROR ===", flush=True)
        print(f"Error: {e}", flush=True)
        print(f"Traceback:\n{error_details}", flush=True)
        print(f"=== END ERROR ===", flush=True)
        logger.error(f"Password reset request error: {e}")
        logger.error(error_details)
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {
                "message": "Failed to process password reset request",
                "error": str(e),
                "type": type(e).__name__
            },
            "nodeId": "opentakserver-password"
        }), 500

@password_bp.route('/reset/verify', methods=['POST'])
def verify_reset_token():
    """
    Verify a password reset token
    POST /Marti/api/password/reset/verify
    Body: {"token": "reset_token"}
    """
    try:
        data = request.get_json()
        if not data or 'token' not in data:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Token is required"},
                "nodeId": "opentakserver-password"
            }), 400
        
        token = data['token']
        
        # Verify token in database
        from opentakserver.magk.services.database import get_database_connection
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, token_expires_at, status
            FROM registration_logs
            WHERE download_token = %s AND status = 'password_reset'
            ORDER BY created_at DESC
            LIMIT 1
        """, (token,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Invalid or expired reset token"},
                "nodeId": "opentakserver-password"
            }), 400
        
        user_id, expires_at, status = result
        
        # Check if token is expired
        if expires_at < datetime.now(timezone.utc):
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Reset token has expired. Please request a new one"},
                "nodeId": "opentakserver-password"
            }), 400
        
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.password.TokenVerification",
            "data": {
                "valid": True,
                "expires_at": expires_at.isoformat()
            },
            "nodeId": "opentakserver-password"
        }), 200
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": "Failed to verify reset token"},
            "nodeId": "opentakserver-password"
        }), 500

@password_bp.route('/reset/confirm', methods=['POST'])
def confirm_password_reset():
    """
    Confirm password reset with new password
    POST /Marti/api/password/reset/confirm
    Body: {"token": "reset_token", "password": "new_password"}
    """
    try:
        data = request.get_json()
        if not data or 'token' not in data or 'password' not in data:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Token and password are required"},
                "nodeId": "opentakserver-password"
            }), 400
        
        token = data['token']
        new_password = data['password']
        
        # Validate new password
        password_util = current_app.security.password_util
        errors, _ = password_util.validate(new_password, is_register=False)
        
        if errors:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {
                    "message": "Password does not meet requirements",
                    "errors": errors
                },
                "nodeId": "opentakserver-password"
            }), 400
        
        # Verify token and get user
        from opentakserver.magk.services.database import get_database_connection
        conn = get_database_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, token_expires_at, status
            FROM registration_logs
            WHERE download_token = %s AND status = 'password_reset'
            ORDER BY created_at DESC
            LIMIT 1
        """, (token,))
        
        result = cursor.fetchone()
        
        if not result:
            cursor.close()
            conn.close()
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Invalid or expired reset token"},
                "nodeId": "opentakserver-password"
            }), 400
        
        user_id, expires_at, status = result
        
        # Check if token is expired
        if expires_at < datetime.now(timezone.utc):
            cursor.close()
            conn.close()
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Reset token has expired. Please request a new one"},
                "nodeId": "opentakserver-password"
            }), 400
        
        # Update user password
        user_datastore = current_app.security.datastore
        user = user_datastore.find_user(id=user_id)
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "User not found"},
                "nodeId": "opentakserver-password"
            }), 404
        
        # Update password
        user.password = hash_password(new_password)
        user_datastore.commit()
        
        # Mark token as used
        cursor.execute("""
            UPDATE registration_logs
            SET status = 'completed', completed_at = %s
            WHERE download_token = %s
        """, (datetime.now(timezone.utc), token))
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Password reset completed for user: {user.username}")
        
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.password.ResetConfirmation",
            "data": {
                "message": "Password has been reset successfully",
                "username": user.username
            },
            "nodeId": "opentakserver-password"
        }), 200
        
    except Exception as e:
        logger.error(f"Password reset confirmation error: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": "Failed to reset password"},
            "nodeId": "opentakserver-password"
        }), 500

@password_bp.route('/change', methods=['POST'])
@auth_required()
def change_password():
    """
    Change password for authenticated user
    POST /Marti/api/password/change
    Body: {"current_password": "old", "new_password": "new"}
    """
    try:
        data = request.get_json()
        if not data or 'current_password' not in data or 'new_password' not in data:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Current password and new password are required"},
                "nodeId": "opentakserver-password"
            }), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Verify current password
        from werkzeug.security import check_password_hash
        if not check_password_hash(current_user.password, current_password):
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {"message": "Current password is incorrect"},
                "nodeId": "opentakserver-password"
            }), 401
        
        # Validate new password
        password_util = current_app.security.password_util
        errors, _ = password_util.validate(new_password, is_register=False)
        
        if errors:
            return jsonify({
                "version": "3",
                "type": "com.bbn.marti.remote.exception.TakException",
                "data": {
                    "message": "New password does not meet requirements",
                    "errors": errors
                },
                "nodeId": "opentakserver-password"
            }), 400
        
        # Update password
        user_datastore = current_app.security.datastore
        current_user.password = hash_password(new_password)
        user_datastore.commit()
        
        logger.info(f"Password changed for user: {current_user.username}")
        
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.password.ChangeConfirmation",
            "data": {
                "message": "Password has been changed successfully",
                "username": current_user.username
            },
            "nodeId": "opentakserver-password"
        }), 200
        
    except Exception as e:
        logger.error(f"Password change error: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": "Failed to change password"},
            "nodeId": "opentakserver-password"
        }), 500

@password_bp.route('/requirements', methods=['GET'])
def get_password_requirements():
    """
    Get password requirements
    GET /Marti/api/password/requirements
    """
    try:
        password_util = current_app.security.password_util
        
        requirements = {
            "min_length": password_util.MIN_LENGTH,
            "requires_uppercase": True,
            "requires_lowercase": True,
            "requires_number": True,
            "requires_special": True,
            "forbidden_characters": ["@", ":"],
            "special_characters": "!#$%&*-_+=?",
            "rules": [
                f"At least {password_util.MIN_LENGTH} characters long",
                "At least one uppercase letter (A-Z)",
                "At least one lowercase letter (a-z)",
                "At least one number (0-9)",
                "At least one special character (!#$%&*-_+=?)",
                "Cannot contain @ or : characters",
                "Cannot be a common password",
                "Cannot contain sequential characters (123, abc)",
                "Cannot contain repeated characters (aaa, 111)"
            ]
        }
        
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.password.Requirements",
            "data": requirements,
            "nodeId": "opentakserver-password"
        }), 200
        
    except Exception as e:
        logger.error(f"Get password requirements error: {e}")
        return jsonify({
            "version": "3",
            "type": "com.bbn.marti.remote.exception.TakException",
            "data": {"message": "Failed to get password requirements"},
            "nodeId": "opentakserver-password"
        }), 500

@password_bp.route('/health', methods=['GET'])
def password_health():
    """Health check for password management system"""
    return jsonify({
        "version": "3",
        "type": "com.bbn.marti.remote.health.Status",
        "data": {
            "status": "healthy",
            "service": "password-management",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "nodeId": "opentakserver-password"
    }), 200
