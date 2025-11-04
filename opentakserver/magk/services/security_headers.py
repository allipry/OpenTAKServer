#!/usr/bin/env python3
"""
Security Headers Service for MAGK-Admin
Implements comprehensive HTTP security headers to protect against common web vulnerabilities
"""

import logging
from flask import Flask
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SecurityHeadersManager:
    """
    Manage HTTP security headers for the application.
    
    This class configures security headers to protect against:
    - Cross-Site Scripting (XSS)
    - Clickjacking
    - MIME type sniffing
    - Information disclosure
    - Man-in-the-middle attacks
    
    Security Headers Implemented:
    - Content-Security-Policy (CSP)
    - X-Frame-Options
    - X-Content-Type-Options
    - Strict-Transport-Security (HSTS)
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """
    
    # Default Content Security Policy
    DEFAULT_CSP = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"],  # Relaxed for Vue.js
        'style-src': ["'self'", "'unsafe-inline'"],  # Relaxed for inline styles
        'img-src': ["'self'", 'data:', 'https:'],
        'font-src': ["'self'", 'data:'],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"]
    }
    
    def __init__(self, app: Optional[Flask] = None, enable_hsts: bool = True):
        """
        Initialize security headers manager.
        
        Args:
            app: Flask application instance (optional)
            enable_hsts: Enable HTTP Strict Transport Security (default: True)
        """
        self.enable_hsts = enable_hsts
        self.csp_policy = self.DEFAULT_CSP.copy()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """
        Initialize security headers for Flask application.
        
        Args:
            app: Flask application instance
        """
        # Register after_request handler to add security headers
        @app.after_request
        def add_security_headers(response):
            return self.apply_security_headers(response)
        
        logger.info("Security headers initialized")
    
    def apply_security_headers(self, response):
        """
        Apply security headers to HTTP response.
        
        Args:
            response: Flask response object
            
        Returns:
            Response object with security headers added
        """
        # Content Security Policy
        csp_header = self._build_csp_header()
        response.headers['Content-Security-Policy'] = csp_header
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection (legacy browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Control referrer information
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature Policy)
        response.headers['Permissions-Policy'] = self._build_permissions_policy()
        
        # HTTP Strict Transport Security (HSTS)
        if self.enable_hsts:
            # 1 year max-age, include subdomains
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Remove server information disclosure
        response.headers.pop('Server', None)
        
        return response
    
    def _build_csp_header(self) -> str:
        """
        Build Content Security Policy header string.
        
        Returns:
            str: CSP header value
        """
        csp_parts = []
        for directive, sources in self.csp_policy.items():
            sources_str = ' '.join(sources)
            csp_parts.append(f"{directive} {sources_str}")
        
        return '; '.join(csp_parts)
    
    def _build_permissions_policy(self) -> str:
        """
        Build Permissions Policy header string.
        
        Returns:
            str: Permissions Policy header value
        """
        # Disable potentially dangerous features
        policies = [
            'geolocation=(self)',  # Allow geolocation for TAK
            'microphone=()',       # Disable microphone
            'camera=()',           # Disable camera
            'payment=()',          # Disable payment
            'usb=()',              # Disable USB
            'magnetometer=()',     # Disable magnetometer
            'gyroscope=()',        # Disable gyroscope
            'accelerometer=()'     # Disable accelerometer
        ]
        
        return ', '.join(policies)
    
    def update_csp(self, directive: str, sources: list):
        """
        Update Content Security Policy directive.
        
        Args:
            directive: CSP directive (e.g., 'script-src')
            sources: List of allowed sources
            
        Example:
            >>> manager = SecurityHeadersManager()
            >>> manager.update_csp('script-src', ["'self'", 'https://cdn.example.com'])
        """
        self.csp_policy[directive] = sources
        logger.info(f"Updated CSP directive: {directive}")
    
    def add_csp_source(self, directive: str, source: str):
        """
        Add a source to existing CSP directive.
        
        Args:
            directive: CSP directive (e.g., 'script-src')
            source: Source to add (e.g., 'https://cdn.example.com')
            
        Example:
            >>> manager = SecurityHeadersManager()
            >>> manager.add_csp_source('script-src', 'https://cdn.example.com')
        """
        if directive not in self.csp_policy:
            self.csp_policy[directive] = []
        
        if source not in self.csp_policy[directive]:
            self.csp_policy[directive].append(source)
            logger.info(f"Added CSP source to {directive}: {source}")
    
    def get_csp_report_uri(self, app: Flask) -> str:
        """
        Get CSP report URI for violation reporting.
        
        Args:
            app: Flask application instance
            
        Returns:
            str: CSP report URI
        """
        # CSP violation reporting endpoint
        return f"{app.config.get('SERVER_URL', '')}/api/csp-report"


def init_security_headers(app: Flask, enable_hsts: bool = True) -> SecurityHeadersManager:
    """
    Initialize security headers for Flask application.
    
    Args:
        app: Flask application instance
        enable_hsts: Enable HTTP Strict Transport Security
        
    Returns:
        SecurityHeadersManager: Configured security headers manager
        
    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> manager = init_security_headers(app)
    """
    manager = SecurityHeadersManager(app, enable_hsts)
    logger.info("Security headers service initialized")
    return manager


# CSP Configuration Presets
CSP_PRESETS = {
    'strict': {
        'default-src': ["'none'"],
        'script-src': ["'self'"],
        'style-src': ["'self'"],
        'img-src': ["'self'"],
        'font-src': ["'self'"],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"]
    },
    'moderate': {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", 'data:', 'https:'],
        'font-src': ["'self'", 'data:'],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"]
    },
    'relaxed': {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", 'data:', 'https:', 'http:'],
        'font-src': ["'self'", 'data:'],
        'connect-src': ["'self'", 'ws:', 'wss:'],
        'frame-ancestors': ["'self'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"]
    }
}


def get_csp_preset(preset_name: str) -> Dict[str, list]:
    """
    Get a predefined CSP configuration preset.
    
    Args:
        preset_name: Name of preset ('strict', 'moderate', 'relaxed')
        
    Returns:
        dict: CSP policy configuration
        
    Example:
        >>> csp = get_csp_preset('moderate')
        >>> manager = SecurityHeadersManager()
        >>> manager.csp_policy = csp
    """
    if preset_name not in CSP_PRESETS:
        logger.warning(f"Unknown CSP preset: {preset_name}, using 'moderate'")
        preset_name = 'moderate'
    
    return CSP_PRESETS[preset_name].copy()
