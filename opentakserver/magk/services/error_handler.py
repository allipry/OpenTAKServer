#!/usr/bin/env python3
"""
Secure Error Handler for MAGK-Admin
Prevents information disclosure through error messages
"""

import logging
import traceback
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from typing import Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SecureErrorHandler:
    """
    Secure error handling that prevents information disclosure.
    
    This class provides error handlers that:
    - Hide sensitive technical details from users
    - Log full error details for debugging
    - Return consistent error response format
    - Prevent stack trace exposure
    - Maintain Marti API compatibility
    
    Security Features:
    - No stack traces in production
    - No database error details exposed
    - No file path information disclosed
    - Consistent error response format
    - Comprehensive server-side logging
    """
    
    def __init__(self, app: Optional[Flask] = None, debug_mode: bool = False):
        """
        Initialize secure error handler.
        
        Args:
            app: Flask application instance (optional)
            debug_mode: Enable detailed errors for development (default: False)
        """
        self.debug_mode = debug_mode
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """
        Initialize error handlers for Flask application.
        
        Args:
            app: Flask application instance
        """
        # Determine if we're in debug mode
        self.debug_mode = app.config.get('DEBUG', False)
        
        # Register error handlers
        app.register_error_handler(400, self.handle_bad_request)
        app.register_error_handler(401, self.handle_unauthorized)
        app.register_error_handler(403, self.handle_forbidden)
        app.register_error_handler(404, self.handle_not_found)
        app.register_error_handler(405, self.handle_method_not_allowed)
        app.register_error_handler(429, self.handle_rate_limit_exceeded)
        app.register_error_handler(500, self.handle_internal_error)
        app.register_error_handler(Exception, self.handle_generic_exception)
        
        logger.info(f"Secure error handlers initialized (debug_mode={self.debug_mode})")
    
    def _create_error_response(self, 
                               status_code: int, 
                               message: str, 
                               error_type: str = "TakException",
                               details: Dict[str, Any] = None) -> Tuple[Dict, int]:
        """
        Create standardized error response.
        
        Args:
            status_code: HTTP status code
            message: User-friendly error message
            error_type: Error type identifier
            details: Additional error details (only in debug mode)
            
        Returns:
            tuple: (response_dict, status_code)
        """
        # Base response in Marti API format
        response = {
            "version": "3",
            "type": f"com.bbn.marti.remote.exception.{error_type}",
            "data": {
                "message": message
            },
            "nodeId": "opentakserver"
        }
        
        # Add details only in debug mode
        if self.debug_mode and details:
            response["data"]["debug"] = details
        
        return response, status_code
    
    def handle_bad_request(self, error):
        """Handle 400 Bad Request errors."""
        logger.warning(f"Bad request: {request.path} - {str(error)}")
        
        response, status_code = self._create_error_response(
            400,
            "Invalid request. Please check your input and try again.",
            "BadRequestException"
        )
        return jsonify(response), status_code
    
    def handle_unauthorized(self, error):
        """Handle 401 Unauthorized errors."""
        logger.warning(f"Unauthorized access attempt: {request.path} - IP: {request.remote_addr}")
        
        response, status_code = self._create_error_response(
            401,
            "Authentication required. Please log in and try again.",
            "UnauthorizedException"
        )
        return jsonify(response), status_code
    
    def handle_forbidden(self, error):
        """Handle 403 Forbidden errors."""
        logger.warning(f"Forbidden access attempt: {request.path} - IP: {request.remote_addr}")
        
        response, status_code = self._create_error_response(
            403,
            "Access denied. You do not have permission to access this resource.",
            "ForbiddenException"
        )
        return jsonify(response), status_code
    
    def handle_not_found(self, error):
        """Handle 404 Not Found errors."""
        logger.info(f"Resource not found: {request.path}")
        
        response, status_code = self._create_error_response(
            404,
            "The requested resource was not found.",
            "NotFoundException"
        )
        return jsonify(response), status_code
    
    def handle_method_not_allowed(self, error):
        """Handle 405 Method Not Allowed errors."""
        logger.warning(f"Method not allowed: {request.method} {request.path}")
        
        response, status_code = self._create_error_response(
            405,
            f"Method {request.method} is not allowed for this endpoint.",
            "MethodNotAllowedException"
        )
        return jsonify(response), status_code
    
    def handle_rate_limit_exceeded(self, error):
        """Handle 429 Rate Limit Exceeded errors."""
        logger.warning(f"Rate limit exceeded: {request.path} - IP: {request.remote_addr}")
        
        response, status_code = self._create_error_response(
            429,
            "Too many requests. Please try again later.",
            "RateLimitException"
        )
        return jsonify(response), status_code
    
    def handle_internal_error(self, error):
        """Handle 500 Internal Server Error."""
        # Log full error details server-side
        logger.error(f"Internal server error: {request.path}", exc_info=True)
        logger.error(f"Error details: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Return generic error to user (no sensitive details)
        details = None
        if self.debug_mode:
            details = {
                "error": str(error),
                "traceback": traceback.format_exc()
            }
        
        response, status_code = self._create_error_response(
            500,
            "An internal error occurred. Please try again later.",
            "InternalServerException",
            details
        )
        return jsonify(response), status_code
    
    def handle_generic_exception(self, error):
        """Handle any unhandled exceptions."""
        # Check if it's an HTTP exception
        if isinstance(error, HTTPException):
            return error
        
        # Log full error details server-side
        logger.error(f"Unhandled exception: {request.path}", exc_info=True)
        logger.error(f"Exception type: {type(error).__name__}")
        logger.error(f"Exception details: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Return generic error to user
        details = None
        if self.debug_mode:
            details = {
                "exception_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc()
            }
        
        response, status_code = self._create_error_response(
            500,
            "An unexpected error occurred. Please try again later.",
            "UnhandledException",
            details
        )
        return jsonify(response), status_code


def init_error_handlers(app: Flask, debug_mode: bool = None) -> SecureErrorHandler:
    """
    Initialize secure error handlers for Flask application.
    
    Args:
        app: Flask application instance
        debug_mode: Override debug mode (default: use app.config['DEBUG'])
        
    Returns:
        SecureErrorHandler: Configured error handler
        
    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> handler = init_error_handlers(app)
    """
    if debug_mode is None:
        debug_mode = app.config.get('DEBUG', False)
    
    handler = SecureErrorHandler(app, debug_mode)
    logger.info("Secure error handlers initialized")
    return handler


def create_error_response(status_code: int, message: str, error_type: str = "TakException") -> Tuple[Dict, int]:
    """
    Create a standardized error response (convenience function).
    
    Args:
        status_code: HTTP status code
        message: User-friendly error message
        error_type: Error type identifier
        
    Returns:
        tuple: (response_dict, status_code)
        
    Example:
        >>> response, code = create_error_response(400, "Invalid input")
        >>> return jsonify(response), code
    """
    response = {
        "version": "3",
        "type": f"com.bbn.marti.remote.exception.{error_type}",
        "data": {
            "message": message
        },
        "nodeId": "opentakserver"
    }
    
    return response, status_code


# Common error messages
ERROR_MESSAGES = {
    'invalid_input': "Invalid input. Please check your data and try again.",
    'authentication_failed': "Authentication failed. Please check your credentials.",
    'account_locked': "Account temporarily locked due to multiple failed login attempts.",
    'rate_limit_exceeded': "Too many requests. Please try again later.",
    'resource_not_found': "The requested resource was not found.",
    'permission_denied': "You do not have permission to perform this action.",
    'internal_error': "An internal error occurred. Please try again later.",
    'database_error': "A database error occurred. Please try again later.",
    'file_upload_error': "File upload failed. Please try again.",
    'certificate_error': "Certificate operation failed. Please contact support."
}


def get_error_message(error_key: str) -> str:
    """
    Get a standardized error message by key.
    
    Args:
        error_key: Error message key
        
    Returns:
        str: Error message
        
    Example:
        >>> message = get_error_message('authentication_failed')
        >>> print(message)
        'Authentication failed. Please check your credentials.'
    """
    return ERROR_MESSAGES.get(error_key, ERROR_MESSAGES['internal_error'])
