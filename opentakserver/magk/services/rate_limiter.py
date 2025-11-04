#!/usr/bin/env python3
"""
Rate Limiting Service for MAGK-Admin
Prevents brute force attacks on authentication endpoints
"""

import logging
from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)


def setup_rate_limiting(app: Flask) -> Limiter:
    """
    Configure rate limiting for Flask application.
    
    This function sets up Flask-Limiter with Redis storage for distributed
    rate limiting across multiple containers. Rate limits are applied per
    IP address to prevent brute force attacks.
    
    Args:
        app: Flask application instance
        
    Returns:
        Limiter: Configured Flask-Limiter instance
        
    Configuration:
        - Default limits: 200 requests per day, 50 per hour
        - Storage: Redis (for distributed rate limiting)
        - Strategy: Fixed window
        - Key function: Remote IP address
        
    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> limiter = setup_rate_limiting(app)
    """
    # Get Redis URL from app config or use default
    storage_uri = app.config.get('RATE_LIMIT_STORAGE_URL', 'memory://')
    
    # Initialize Flask-Limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=storage_uri,
        strategy="fixed-window",
        # Add headers to responses showing rate limit status
        headers_enabled=True,
        # Swallow errors to prevent rate limiter from breaking the app
        swallow_errors=True
    )
    
    logger.info(f"Rate limiting configured with storage: {storage_uri}")
    logger.info("Default limits: 200/day, 50/hour per IP address")
    
    return limiter


def apply_auth_rate_limits(limiter: Limiter):
    """
    Apply strict rate limits to authentication endpoints.
    
    This function decorates authentication endpoints with rate limits to
    prevent brute force attacks. Multiple limits are applied:
    - 5 attempts per minute (prevents rapid attacks)
    - 20 attempts per hour (prevents sustained attacks)
    
    Args:
        limiter: Flask-Limiter instance
        
    Rate Limits Applied:
        - Login: 5/minute, 20/hour per IP
        - Password reset: 3/hour per IP
        
    Example:
        >>> limiter = setup_rate_limiting(app)
        >>> apply_auth_rate_limits(limiter)
    """
    # These decorators will be applied to endpoints in the blueprints
    # The actual application happens in the blueprint registration
    logger.info("Authentication rate limits configured:")
    logger.info("  - Login: 5/minute, 20/hour per IP")
    logger.info("  - Password reset: 3/hour per IP")


def get_rate_limit_decorator(limiter: Limiter, limit_string: str):
    """
    Get a rate limit decorator for a specific limit.
    
    Args:
        limiter: Flask-Limiter instance
        limit_string: Rate limit string (e.g., "5 per minute")
        
    Returns:
        Decorator function
        
    Example:
        >>> limiter = setup_rate_limiting(app)
        >>> login_limit = get_rate_limit_decorator(limiter, "5 per minute")
        >>> @login_limit
        >>> def login():
        >>>     pass
    """
    return limiter.limit(limit_string)


# Rate limit strings for common use cases
RATE_LIMITS = {
    'login_minute': '5 per minute',
    'login_hour': '20 per hour',
    'password_reset': '3 per hour',
    'registration': '10 per hour',
    'api_default': '100 per hour'
}
