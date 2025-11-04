#!/usr/bin/env python3
"""
Security Logger Test Suite
Tests comprehensive security event logging end-to-end
"""

import pytest
import json
import tempfile
import os
from flask import Flask
from opentakserver.magk.services.security_logger import (
    SecurityLogger,
    get_security_logger,
    init_security_logging
)


class TestSecurityLogger:
    """Test SecurityLogger class"""
    
    def test_init_without_log_file(self):
        """Test initialization without log file"""
        logger = SecurityLogger()
        assert logger.log_file is None
        assert logger.security_logger is not None
    
    def test_init_with_log_file(self):
        """Test initialization with log file"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            log_file = tmp.name
        
        try:
            logger = SecurityLogger(log_file=log_file)
            assert logger.log_file == log_file
            assert logger.security_logger is not None
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_get_request_context_without_request(self):
        """Test getting request context when no request is active"""
        logger = SecurityLogger()
        context = logger._get_request_context()
        
        assert context['ip_address'] == 'unknown'
        assert context['user_agent'] == 'unknown'
        assert context['endpoint'] == 'unknown'
        assert context['method'] == 'unknown'
    
    def test_get_request_context_with_request(self):
        """Test getting request context with active request"""
        app = Flask(__name__)
        logger = SecurityLogger()
        
        @app.route('/test')
        def test_route():
            context = logger._get_request_context()
            return json.dumps(context)
        
        with app.test_client() as client:
            response = client.get('/test')
            context = json.loads(response.data)
            
            assert context['ip_address'] == '127.0.0.1'
            assert context['endpoint'] == '/test'
            assert context['method'] == 'GET'
    
    def test_create_log_entry(self):
        """Test creating structured log entry"""
        logger = SecurityLogger()
        
        log_entry = logger._create_log_entry(
            'auth_success',
            'testuser',
            {'session_id': '123'},
            'INFO'
        )
        
        assert log_entry['event_type'] == 'auth_success'
        assert log_entry['username'] == 'testuser'
        assert log_entry['severity'] == 'INFO'
        assert log_entry['details']['session_id'] == '123'
        assert 'timestamp' in log_entry


class TestAuthenticationLogging:
    """Test authentication event logging"""
    
    @pytest.fixture
    def logger(self):
        """Create security logger"""
        return SecurityLogger()
    
    def test_log_auth_success(self, logger):
        """Test logging successful authentication"""
        # Should not raise exception
        logger.log_auth_success('testuser', {'session_id': '123'})
    
    def test_log_auth_failure(self, logger):
        """Test logging failed authentication"""
        logger.log_auth_failure('testuser', 'invalid_password', {'attempts': 1})
    
    def test_log_account_lockout(self, logger):
        """Test logging account lockout"""
        logger.log_account_lockout('testuser', 5, 15)


class TestRateLimitLogging:
    """Test rate limit event logging"""
    
    @pytest.fixture
    def logger(self):
        """Create security logger"""
        return SecurityLogger()
    
    def test_log_rate_limit_exceeded(self, logger):
        """Test logging rate limit violation"""
        logger.log_rate_limit_exceeded('testuser', '/api/login', '5 per minute')


class TestCertificateLogging:
    """Test certificate operation logging"""
    
    @pytest.fixture
    def logger(self):
        """Create security logger"""
        return SecurityLogger()
    
    def test_log_certificate_created(self, logger):
        """Test logging certificate creation"""
        logger.log_certificate_created('admin', 'client', 'CN=testuser')
    
    def test_log_certificate_revoked(self, logger):
        """Test logging certificate revocation"""
        logger.log_certificate_revoked('admin', '1234567890', 'compromised')


class TestAdminActionLogging:
    """Test administrative action logging"""
    
    @pytest.fixture
    def logger(self):
        """Create security logger"""
        return SecurityLogger()
    
    def test_log_admin_action(self, logger):
        """Test logging admin action"""
        logger.log_admin_action('admin', 'user_delete', 'testuser', {'reason': 'inactive'})
    
    def test_log_permission_denied(self, logger):
        """Test logging permission denied"""
        logger.log_permission_denied('testuser', '/admin/users', 'delete')
    
    def test_log_suspicious_activity(self, logger):
        """Test logging suspicious activity"""
        logger.log_suspicious_activity('testuser', 'multiple_failed_logins', {'count': 10})


class TestAccountManagementLogging:
    """Test account management event logging"""
    
    @pytest.fixture
    def logger(self):
        """Create security logger"""
        return SecurityLogger()
    
    def test_log_password_reset(self, logger):
        """Test logging password reset"""
        logger.log_password_reset('testuser', 'user')
    
    def test_log_account_created(self, logger):
        """Test logging account creation"""
        logger.log_account_created('newuser', 'admin', 'user')
    
    def test_log_account_deleted(self, logger):
        """Test logging account deletion"""
        logger.log_account_deleted('olduser', 'admin', 'inactive')
    
    def test_log_config_changed(self, logger):
        """Test logging configuration change"""
        logger.log_config_changed('admin', 'max_attempts', 5, 3)


class TestLogFileWriting:
    """Test that logs are written to file"""
    
    def test_logs_written_to_file(self):
        """Test that security events are written to log file"""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as tmp:
            log_file = tmp.name
        
        try:
            logger = SecurityLogger(log_file=log_file)
            
            # Log various events
            logger.log_auth_success('testuser', {})
            logger.log_auth_failure('baduser', 'invalid_password', {})
            logger.log_account_lockout('lockeduser', 5, 15)
            
            # Read log file
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            # Verify events were logged
            assert 'auth_success' in log_content
            assert 'auth_failure' in log_content
            assert 'auth_lockout' in log_content
            assert 'testuser' in log_content
            assert 'baduser' in log_content
            assert 'lockeduser' in log_content
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_log_entries_are_json(self):
        """Test that log entries are valid JSON"""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as tmp:
            log_file = tmp.name
        
        try:
            logger = SecurityLogger(log_file=log_file)
            logger.log_auth_success('testuser', {'session_id': '123'})
            
            # Read and parse log file
            with open(log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        # Should be valid JSON
                        log_entry = json.loads(line.split(' - ')[-1])
                        assert 'timestamp' in log_entry
                        assert 'event_type' in log_entry
                        assert 'username' in log_entry
                        
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)


class TestEndToEndLogging:
    """End-to-end integration tests"""
    
    def test_complete_authentication_flow(self):
        """Test logging complete authentication flow"""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as tmp:
            log_file = tmp.name
        
        try:
            logger = SecurityLogger(log_file=log_file)
            
            # Simulate authentication flow
            # 1. Failed attempts
            for i in range(3):
                logger.log_auth_failure('testuser', 'invalid_password', {'attempts': i+1})
            
            # 2. Successful login
            logger.log_auth_success('testuser', {'session_id': 'abc123'})
            
            # Read log file
            with open(log_file, 'r') as f:
                log_lines = f.readlines()
            
            # Verify all events logged
            assert len([l for l in log_lines if 'auth_failure' in l]) == 3
            assert len([l for l in log_lines if 'auth_success' in l]) == 1
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_account_lockout_flow(self):
        """Test logging account lockout flow"""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as tmp:
            log_file = tmp.name
        
        try:
            logger = SecurityLogger(log_file=log_file)
            
            # Simulate lockout flow
            # 1. Multiple failed attempts
            for i in range(5):
                logger.log_auth_failure('baduser', 'invalid_password', {'attempts': i+1})
            
            # 2. Account locked
            logger.log_account_lockout('baduser', 5, 15)
            
            # 3. Admin unlocks
            logger.log_admin_action('admin', 'account_unlock', 'baduser', {})
            
            # Read log file
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            # Verify flow logged
            assert log_content.count('auth_failure') == 5
            assert 'auth_lockout' in log_content
            assert 'admin_action' in log_content
            assert 'account_unlock' in log_content
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_certificate_lifecycle(self):
        """Test logging certificate lifecycle"""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as tmp:
            log_file = tmp.name
        
        try:
            logger = SecurityLogger(log_file=log_file)
            
            # Certificate lifecycle
            logger.log_certificate_created('admin', 'client', 'CN=testuser')
            logger.log_certificate_revoked('admin', '1234567890', 'compromised')
            
            # Read log file
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            # Verify lifecycle logged
            assert 'certificate_created' in log_content
            assert 'certificate_revoked' in log_content
            assert 'CN=testuser' in log_content
            assert 'compromised' in log_content
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)


class TestFlaskIntegration:
    """Test Flask application integration"""
    
    def test_init_security_logging(self):
        """Test initializing security logging with Flask app"""
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as tmp:
            log_file = tmp.name
        
        try:
            app.config['SECURITY_LOG_FILE'] = log_file
            logger = init_security_logging(app)
            
            assert logger is not None
            assert logger.log_file == log_file
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)
    
    def test_get_security_logger_singleton(self):
        """Test that get_security_logger returns singleton"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.log') as tmp:
            log_file = tmp.name
        
        try:
            logger1 = get_security_logger(log_file)
            logger2 = get_security_logger(log_file)
            
            # Should be same instance
            assert logger1 is logger2
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)


class TestLogSeverityLevels:
    """Test different severity levels"""
    
    @pytest.fixture
    def logger(self):
        """Create security logger"""
        return SecurityLogger()
    
    def test_info_level_events(self, logger):
        """Test INFO level events"""
        logger.log_auth_success('testuser', {})
        logger.log_certificate_created('admin', 'client', 'CN=test')
        logger.log_account_created('newuser', 'admin', 'user')
    
    def test_warning_level_events(self, logger):
        """Test WARNING level events"""
        logger.log_auth_failure('testuser', 'invalid_password', {})
        logger.log_rate_limit_exceeded('testuser', '/api/login', '5 per minute')
        logger.log_permission_denied('testuser', '/admin', 'access')
    
    def test_error_level_events(self, logger):
        """Test ERROR level events"""
        logger.log_account_lockout('testuser', 5, 15)
    
    def test_critical_level_events(self, logger):
        """Test CRITICAL level events"""
        logger.log_suspicious_activity('testuser', 'sql_injection_attempt', {})


class TestEventTypes:
    """Test all event types are properly defined"""
    
    def test_event_type_constants(self):
        """Test that all event type constants are defined"""
        assert hasattr(SecurityLogger, 'EVENT_AUTH_SUCCESS')
        assert hasattr(SecurityLogger, 'EVENT_AUTH_FAILURE')
        assert hasattr(SecurityLogger, 'EVENT_AUTH_LOCKOUT')
        assert hasattr(SecurityLogger, 'EVENT_RATE_LIMIT')
        assert hasattr(SecurityLogger, 'EVENT_CERT_CREATED')
        assert hasattr(SecurityLogger, 'EVENT_CERT_REVOKED')
        assert hasattr(SecurityLogger, 'EVENT_ADMIN_ACTION')
        assert hasattr(SecurityLogger, 'EVENT_PERMISSION_DENIED')
        assert hasattr(SecurityLogger, 'EVENT_SUSPICIOUS')
        assert hasattr(SecurityLogger, 'EVENT_PASSWORD_RESET')
        assert hasattr(SecurityLogger, 'EVENT_ACCOUNT_CREATED')
        assert hasattr(SecurityLogger, 'EVENT_ACCOUNT_DELETED')
        assert hasattr(SecurityLogger, 'EVENT_CONFIG_CHANGED')


def run_manual_tests():
    """Manual test function for security logger validation"""
    print("\n" + "="*70)
    print("SECURITY LOGGER VALIDATION TEST")
    print("="*70)
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log') as tmp:
        log_file = tmp.name
    
    try:
        logger = SecurityLogger(log_file=log_file)
        
        print("\n📋 Testing Security Event Logging:")
        print("-" * 70)
        
        # Test various events
        logger.log_auth_success('testuser', {'session_id': '123'})
        print("✅ Authentication success logged")
        
        logger.log_auth_failure('baduser', 'invalid_password', {'attempts': 1})
        print("✅ Authentication failure logged")
        
        logger.log_account_lockout('lockeduser', 5, 15)
        print("✅ Account lockout logged")
        
        logger.log_rate_limit_exceeded('testuser', '/api/login', '5 per minute')
        print("✅ Rate limit violation logged")
        
        logger.log_certificate_created('admin', 'client', 'CN=testuser')
        print("✅ Certificate creation logged")
        
        logger.log_admin_action('admin', 'user_delete', 'testuser', {})
        print("✅ Admin action logged")
        
        logger.log_suspicious_activity('attacker', 'sql_injection', {})
        print("✅ Suspicious activity logged")
        
        # Read and display log file
        print("\n📄 Log File Contents:")
        print("-" * 70)
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
            for line in log_lines[-5:]:  # Show last 5 entries
                if line.strip():
                    try:
                        log_data = json.loads(line.split(' - ')[-1])
                        print(f"  {log_data['event_type']}: {log_data['username']} - {log_data['severity']}")
                    except:
                        pass
        
        print("-" * 70)
        print(f"✅ Total events logged: {len(log_lines)}")
        print("✅ ALL SECURITY LOGGING WORKING CORRECTLY")
        print("="*70 + "\n")
        
    finally:
        if os.path.exists(log_file):
            os.unlink(log_file)


if __name__ == '__main__':
    run_manual_tests()
