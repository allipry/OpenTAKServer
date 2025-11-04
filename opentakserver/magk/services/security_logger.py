#!/usr/bin/env python3
"""
Security Logger for MAGK-Admin
Comprehensive security event logging for audit and monitoring
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request, has_request_context

logger = logging.getLogger(__name__)


class SecurityLogger:
    """
    Centralized security event logging.
    
    This class provides structured logging for security-relevant events:
    - Authentication attempts (success/failure)
    - Authorization failures
    - Account lockouts
    - Rate limit violations
    - Certificate operations
    - Administrative actions
    - Suspicious activity
    
    Log Format:
    - Timestamp (ISO 8601)
    - Event type
    - User identifier
    - IP address
    - User agent
    - Event details
    - Severity level
    """
    
    # Event types
    EVENT_AUTH_SUCCESS = "auth_success"
    EVENT_AUTH_FAILURE = "auth_failure"
    EVENT_AUTH_LOCKOUT = "auth_lockout"
    EVENT_RATE_LIMIT = "rate_limit_exceeded"
    EVENT_CERT_CREATED = "certificate_created"
    EVENT_CERT_REVOKED = "certificate_revoked"
    EVENT_ADMIN_ACTION = "admin_action"
    EVENT_PERMISSION_DENIED = "permission_denied"
    EVENT_SUSPICIOUS = "suspicious_activity"
    EVENT_PASSWORD_RESET = "password_reset"
    EVENT_ACCOUNT_CREATED = "account_created"
    EVENT_ACCOUNT_DELETED = "account_deleted"
    EVENT_CONFIG_CHANGED = "config_changed"
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize security logger.
        
        Args:
            log_file: Path to security log file (optional)
        """
        self.log_file = log_file
        
        # Create dedicated security logger
        self.security_logger = logging.getLogger('security')
        self.security_logger.setLevel(logging.INFO)
        
        # Add file handler if log file specified
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            self.security_logger.addHandler(handler)
        
        logger.info(f"Security logger initialized (log_file={log_file})")
    
    def _get_request_context(self) -> Dict[str, Any]:
        """
        Get current request context information.
        
        Returns:
            dict: Request context (IP, user agent, endpoint)
        """
        if not has_request_context():
            return {
                'ip_address': 'unknown',
                'user_agent': 'unknown',
                'endpoint': 'unknown',
                'method': 'unknown'
            }
        
        return {
            'ip_address': request.remote_addr or 'unknown',
            'user_agent': request.headers.get('User-Agent', 'unknown'),
            'endpoint': request.path,
            'method': request.method
        }
    
    def _create_log_entry(self, 
                         event_type: str, 
                         username: Optional[str], 
                         details: Dict[str, Any],
                         severity: str = 'INFO') -> Dict[str, Any]:
        """
        Create structured log entry.
        
        Args:
            event_type: Type of security event
            username: Username involved (if applicable)
            details: Event-specific details
            severity: Log severity level
            
        Returns:
            dict: Structured log entry
        """
        context = self._get_request_context()
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'username': username or 'anonymous',
            'ip_address': context['ip_address'],
            'user_agent': context['user_agent'],
            'endpoint': context['endpoint'],
            'method': context['method'],
            'severity': severity,
            'details': details
        }
        
        return log_entry
    
    def _log_event(self, log_entry: Dict[str, Any]):
        """
        Write log entry to security log.
        
        Args:
            log_entry: Structured log entry
        """
        # Log as JSON for easy parsing
        log_message = json.dumps(log_entry)
        
        # Log at appropriate level
        severity = log_entry.get('severity', 'INFO')
        if severity == 'CRITICAL':
            self.security_logger.critical(log_message)
        elif severity == 'ERROR':
            self.security_logger.error(log_message)
        elif severity == 'WARNING':
            self.security_logger.warning(log_message)
        else:
            self.security_logger.info(log_message)
    
    def log_auth_success(self, username: str, details: Dict[str, Any] = None):
        """
        Log successful authentication.
        
        Args:
            username: Username that authenticated
            details: Additional details
        """
        log_entry = self._create_log_entry(
            self.EVENT_AUTH_SUCCESS,
            username,
            details or {},
            'INFO'
        )
        self._log_event(log_entry)
    
    def log_auth_failure(self, username: str, reason: str, details: Dict[str, Any] = None):
        """
        Log failed authentication attempt.
        
        Args:
            username: Username that failed authentication
            reason: Failure reason
            details: Additional details
        """
        log_entry = self._create_log_entry(
            self.EVENT_AUTH_FAILURE,
            username,
            {
                'reason': reason,
                **(details or {})
            },
            'WARNING'
        )
        self._log_event(log_entry)
    
    def log_account_lockout(self, username: str, attempts: int, lockout_duration: int):
        """
        Log account lockout event.
        
        Args:
            username: Username that was locked
            attempts: Number of failed attempts
            lockout_duration: Lockout duration in minutes
        """
        log_entry = self._create_log_entry(
            self.EVENT_AUTH_LOCKOUT,
            username,
            {
                'failed_attempts': attempts,
                'lockout_duration_minutes': lockout_duration
            },
            'ERROR'
        )
        self._log_event(log_entry)
    
    def log_rate_limit_exceeded(self, username: Optional[str], endpoint: str, limit: str):
        """
        Log rate limit violation.
        
        Args:
            username: Username (if authenticated)
            endpoint: Endpoint that was rate limited
            limit: Rate limit that was exceeded
        """
        log_entry = self._create_log_entry(
            self.EVENT_RATE_LIMIT,
            username,
            {
                'endpoint': endpoint,
                'limit': limit
            },
            'WARNING'
        )
        self._log_event(log_entry)
    
    def log_certificate_created(self, username: str, cert_type: str, subject: str):
        """
        Log certificate creation.
        
        Args:
            username: Username that created certificate
            cert_type: Type of certificate (client, server, CA)
            subject: Certificate subject
        """
        log_entry = self._create_log_entry(
            self.EVENT_CERT_CREATED,
            username,
            {
                'cert_type': cert_type,
                'subject': subject
            },
            'INFO'
        )
        self._log_event(log_entry)
    
    def log_certificate_revoked(self, username: str, cert_serial: str, reason: str):
        """
        Log certificate revocation.
        
        Args:
            username: Username that revoked certificate
            cert_serial: Certificate serial number
            reason: Revocation reason
        """
        log_entry = self._create_log_entry(
            self.EVENT_CERT_REVOKED,
            username,
            {
                'cert_serial': cert_serial,
                'reason': reason
            },
            'WARNING'
        )
        self._log_event(log_entry)
    
    def log_admin_action(self, username: str, action: str, target: str, details: Dict[str, Any] = None):
        """
        Log administrative action.
        
        Args:
            username: Administrator username
            action: Action performed
            target: Target of action (user, config, etc.)
            details: Additional details
        """
        log_entry = self._create_log_entry(
            self.EVENT_ADMIN_ACTION,
            username,
            {
                'action': action,
                'target': target,
                **(details or {})
            },
            'WARNING'
        )
        self._log_event(log_entry)
    
    def log_permission_denied(self, username: str, resource: str, action: str):
        """
        Log permission denied event.
        
        Args:
            username: Username that was denied
            resource: Resource that was accessed
            action: Action that was attempted
        """
        log_entry = self._create_log_entry(
            self.EVENT_PERMISSION_DENIED,
            username,
            {
                'resource': resource,
                'action': action
            },
            'WARNING'
        )
        self._log_event(log_entry)
    
    def log_suspicious_activity(self, username: Optional[str], activity: str, details: Dict[str, Any] = None):
        """
        Log suspicious activity.
        
        Args:
            username: Username involved (if known)
            activity: Description of suspicious activity
            details: Additional details
        """
        log_entry = self._create_log_entry(
            self.EVENT_SUSPICIOUS,
            username,
            {
                'activity': activity,
                **(details or {})
            },
            'CRITICAL'
        )
        self._log_event(log_entry)
    
    def log_password_reset(self, username: str, initiated_by: str):
        """
        Log password reset event.
        
        Args:
            username: Username whose password was reset
            initiated_by: Who initiated the reset (user or admin)
        """
        log_entry = self._create_log_entry(
            self.EVENT_PASSWORD_RESET,
            username,
            {
                'initiated_by': initiated_by
            },
            'WARNING'
        )
        self._log_event(log_entry)
    
    def log_account_created(self, username: str, created_by: str, role: str):
        """
        Log account creation.
        
        Args:
            username: Username that was created
            created_by: Who created the account
            role: Account role
        """
        log_entry = self._create_log_entry(
            self.EVENT_ACCOUNT_CREATED,
            username,
            {
                'created_by': created_by,
                'role': role
            },
            'INFO'
        )
        self._log_event(log_entry)
    
    def log_account_deleted(self, username: str, deleted_by: str, reason: str):
        """
        Log account deletion.
        
        Args:
            username: Username that was deleted
            deleted_by: Who deleted the account
            reason: Deletion reason
        """
        log_entry = self._create_log_entry(
            self.EVENT_ACCOUNT_DELETED,
            username,
            {
                'deleted_by': deleted_by,
                'reason': reason
            },
            'WARNING'
        )
        self._log_event(log_entry)
    
    def log_config_changed(self, username: str, config_key: str, old_value: Any, new_value: Any):
        """
        Log configuration change.
        
        Args:
            username: Username that changed config
            config_key: Configuration key that was changed
            old_value: Previous value
            new_value: New value
        """
        log_entry = self._create_log_entry(
            self.EVENT_CONFIG_CHANGED,
            username,
            {
                'config_key': config_key,
                'old_value': str(old_value),
                'new_value': str(new_value)
            },
            'WARNING'
        )
        self._log_event(log_entry)


# Global security logger instance
_security_logger = None


def get_security_logger(log_file: Optional[str] = None) -> SecurityLogger:
    """
    Get or create the global security logger instance.
    
    Args:
        log_file: Path to security log file
        
    Returns:
        SecurityLogger: Global security logger instance
    """
    global _security_logger
    
    if _security_logger is None:
        _security_logger = SecurityLogger(log_file)
    
    return _security_logger


def init_security_logging(app):
    """
    Initialize security logging for Flask application.
    
    Args:
        app: Flask application instance
        
    Returns:
        SecurityLogger: Configured security logger
    """
    log_file = app.config.get('SECURITY_LOG_FILE', '/var/log/opentakserver/security.log')
    return get_security_logger(log_file)
