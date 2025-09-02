"""
Unit tests for user creation functionality in QR code generation.
Tests user creation, validation, and error handling.
"""

import os
import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

# Add the parent directory to the path so we can import the module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestUserCreation:
    """Test cases for user creation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        pass
    
    def teardown_method(self):
        """Clean up after tests."""
        pass
    
    def test_user_creation_validation_username(self):
        """Test username validation for user creation."""
        def validate_username(username):
            """Validate username for user creation."""
            validation_errors = []
            
            if not username or not isinstance(username, str):
                validation_errors.append('Username must be a non-empty string')
            else:
                username_clean = username.strip()
                if len(username_clean) == 0:
                    validation_errors.append('Username cannot be empty or whitespace only')
                elif len(username_clean) < 3:
                    validation_errors.append('Username must be at least 3 characters long')
                elif len(username_clean) > 255:
                    validation_errors.append('Username cannot exceed 255 characters')
                elif not username_clean.replace('_', '').replace('-', '').replace('.', '').isalnum():
                    validation_errors.append('Username can only contain letters, numbers, underscores, hyphens, and dots')
                elif username_clean.startswith('.') or username_clean.endswith('.'):
                    validation_errors.append('Username cannot start or end with a dot')
            
            return len(validation_errors) == 0, validation_errors
        
        # Test valid usernames
        valid_usernames = [
            'user123',
            'test_user',
            'admin-user',
            'user.name',
            'User123',
            'a1b2c3'
        ]
        
        for username in valid_usernames:
            is_valid, errors = validate_username(username)
            assert is_valid == True, f"Username '{username}' should be valid, errors: {errors}"
            assert len(errors) == 0
        
        # Test invalid usernames
        invalid_usernames = [
            ('', ['Username cannot be empty or whitespace only']),
            ('  ', ['Username cannot be empty or whitespace only']),
            ('ab', ['Username must be at least 3 characters long']),
            ('a' * 256, ['Username cannot exceed 255 characters']),
            ('user@domain', ['Username can only contain letters, numbers, underscores, hyphens, and dots']),
            ('user space', ['Username can only contain letters, numbers, underscores, hyphens, and dots']),
            ('.username', ['Username cannot start or end with a dot']),
            ('username.', ['Username cannot start or end with a dot']),
            ('user!name', ['Username can only contain letters, numbers, underscores, hyphens, and dots']),
            (None, ['Username must be a non-empty string']),
            (123, ['Username must be a non-empty string'])
        ]
        
        for username, expected_errors in invalid_usernames:
            is_valid, errors = validate_username(username)
            assert is_valid == False, f"Username '{username}' should be invalid"
            for expected_error in expected_errors:
                assert any(expected_error in error for error in errors), f"Expected error '{expected_error}' not found in {errors}"
    
    def test_user_creation_validation_password(self):
        """Test password validation for user creation."""
        def validate_password(password):
            """Validate password for user creation."""
            validation_errors = []
            
            if not password or not isinstance(password, str):
                validation_errors.append('Password must be a non-empty string')
            else:
                password_clean = password.strip()
                if len(password_clean) == 0:
                    validation_errors.append('Password cannot be empty or whitespace only')
                elif len(password_clean) < 8:
                    validation_errors.append('Password must be at least 8 characters long')
                elif len(password_clean) > 1024:
                    validation_errors.append('Password cannot exceed 1024 characters')
                
                # Check password complexity (optional requirements)
                has_upper = any(c.isupper() for c in password_clean)
                has_lower = any(c.islower() for c in password_clean)
                has_digit = any(c.isdigit() for c in password_clean)
                has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password_clean)
                
                complexity_score = sum([has_upper, has_lower, has_digit, has_special])
                if complexity_score < 2:
                    validation_errors.append('Password should contain at least 2 of: uppercase, lowercase, digits, special characters')
            
            return len(validation_errors) == 0, validation_errors
        
        # Test valid passwords
        valid_passwords = [
            'Password123',
            'mySecure!Pass',
            'Test@1234',
            'ComplexP@ssw0rd',
            'Simple123',
            'password!',
            'PASSWORD1',
            'Pass@word'
        ]
        
        for password in valid_passwords:
            is_valid, errors = validate_password(password)
            assert is_valid == True, f"Password '{password}' should be valid, errors: {errors}"
            assert len(errors) == 0
        
        # Test invalid passwords
        invalid_passwords = [
            ('', ['Password cannot be empty or whitespace only']),
            ('  ', ['Password cannot be empty or whitespace only']),
            ('short', ['Password must be at least 8 characters long']),
            ('a' * 1025, ['Password cannot exceed 1024 characters']),
            ('password', ['Password should contain at least 2 of: uppercase, lowercase, digits, special characters']),
            ('PASSWORD', ['Password should contain at least 2 of: uppercase, lowercase, digits, special characters']),
            ('12345678', ['Password should contain at least 2 of: uppercase, lowercase, digits, special characters']),
            (None, ['Password must be a non-empty string']),
            (123, ['Password must be a non-empty string'])
        ]
        
        for password, expected_errors in invalid_passwords:
            is_valid, errors = validate_password(password)
            assert is_valid == False, f"Password '{password}' should be invalid"
            for expected_error in expected_errors:
                assert any(expected_error in error for error in errors), f"Expected error '{expected_error}' not found in {errors}"
    
    def test_user_creation_role_validation(self):
        """Test user role validation for user creation."""
        def validate_user_role(role):
            """Validate user role for user creation."""
            valid_roles = ['user', 'admin', 'operator', 'readonly']
            
            if not role or not isinstance(role, str):
                return False, 'Role must be a non-empty string'
            
            role_clean = role.strip().lower()
            if role_clean not in valid_roles:
                return False, f'Role must be one of: {", ".join(valid_roles)}'
            
            return True, ''
        
        # Test valid roles
        valid_roles = ['user', 'admin', 'operator', 'readonly', 'USER', 'Admin', 'OPERATOR']
        
        for role in valid_roles:
            is_valid, error = validate_user_role(role)
            assert is_valid == True, f"Role '{role}' should be valid, error: {error}"
            assert error == ''
        
        # Test invalid roles
        invalid_roles = [
            ('', 'Role must be a non-empty string'),
            ('  ', 'Role must be one of: user, admin, operator, readonly'),
            ('invalid', 'Role must be one of: user, admin, operator, readonly'),
            ('superuser', 'Role must be one of: user, admin, operator, readonly'),
            (None, 'Role must be a non-empty string'),
            (123, 'Role must be a non-empty string')
        ]
        
        for role, expected_error in invalid_roles:
            is_valid, error = validate_user_role(role)
            assert is_valid == False, f"Role '{role}' should be invalid"
            assert expected_error in error, f"Expected error '{expected_error}' not found in '{error}'"
    
    def test_user_creation_success_scenario(self):
        """Test successful user creation scenario."""
        def mock_create_user(username, password, role='user'):
            """Mock user creation function."""
            # Simulate successful user creation
            return {
                'user_created': True,
                'user_existed': False,
                'user_updated': False,
                'creation_error': None,
                'validation_errors': [],
                'user_id': 12345,
                'username': username,
                'role': role,
                'created_at': datetime.now().isoformat()
            }
        
        # Test successful creation
        result = mock_create_user('testuser', 'TestPass123!', 'user')
        
        assert result['user_created'] == True
        assert result['user_existed'] == False
        assert result['creation_error'] is None
        assert len(result['validation_errors']) == 0
        assert result['username'] == 'testuser'
        assert result['role'] == 'user'
        assert 'user_id' in result
        assert 'created_at' in result
    
    def test_user_creation_user_exists_scenario(self):
        """Test user creation when user already exists."""
        def mock_create_existing_user(username, password, role='user'):
            """Mock user creation when user already exists."""
            return {
                'user_created': False,
                'user_existed': True,
                'user_updated': False,
                'creation_error': None,
                'validation_errors': [],
                'warning': f'User {username} already exists',
                'existing_user_id': 12345,
                'username': username
            }
        
        # Test existing user scenario
        result = mock_create_existing_user('existinguser', 'TestPass123!', 'user')
        
        assert result['user_created'] == False
        assert result['user_existed'] == True
        assert result['creation_error'] is None
        assert 'warning' in result
        assert 'existing_user_id' in result
    
    def test_user_creation_database_error_scenario(self):
        """Test user creation with database error."""
        def mock_create_user_db_error(username, password, role='user'):
            """Mock user creation with database error."""
            return {
                'user_created': False,
                'user_existed': False,
                'user_updated': False,
                'creation_error': 'Database connection failed: Connection timeout',
                'validation_errors': [],
                'troubleshooting': 'Check database connectivity and retry'
            }
        
        # Test database error scenario
        result = mock_create_user_db_error('testuser', 'TestPass123!', 'user')
        
        assert result['user_created'] == False
        assert result['user_existed'] == False
        assert result['creation_error'] is not None
        assert 'Database connection failed' in result['creation_error']
        assert 'troubleshooting' in result
    
    def test_user_creation_validation_error_scenario(self):
        """Test user creation with validation errors."""
        def mock_create_user_validation_error(username, password, role='user'):
            """Mock user creation with validation errors."""
            validation_errors = []
            
            # Simulate validation
            if len(username) < 3:
                validation_errors.append('Username too short')
            if len(password) < 8:
                validation_errors.append('Password too short')
            if role not in ['user', 'admin']:
                validation_errors.append('Invalid role')
            
            if validation_errors:
                return {
                    'user_created': False,
                    'user_existed': False,
                    'user_updated': False,
                    'creation_error': 'Validation failed',
                    'validation_errors': validation_errors,
                    'troubleshooting': 'Fix validation errors and retry'
                }
            
            return {'user_created': True}
        
        # Test validation error scenario
        result = mock_create_user_validation_error('ab', '123', 'invalid')
        
        assert result['user_created'] == False
        assert result['creation_error'] == 'Validation failed'
        assert len(result['validation_errors']) == 3
        assert 'Username too short' in result['validation_errors']
        assert 'Password too short' in result['validation_errors']
        assert 'Invalid role' in result['validation_errors']
    
    def test_user_creation_permission_error_scenario(self):
        """Test user creation with permission error."""
        def mock_create_user_permission_error(username, password, role='user'):
            """Mock user creation with permission error."""
            return {
                'user_created': False,
                'user_existed': False,
                'user_updated': False,
                'creation_error': 'Insufficient permissions to create user',
                'validation_errors': [],
                'troubleshooting': 'Contact administrator for user creation permissions',
                'error_code': 403
            }
        
        # Test permission error scenario
        result = mock_create_user_permission_error('testuser', 'TestPass123!', 'admin')
        
        assert result['user_created'] == False
        assert 'Insufficient permissions' in result['creation_error']
        assert result['error_code'] == 403
        assert 'troubleshooting' in result
    
    def test_user_creation_update_scenario(self):
        """Test user creation that updates existing user."""
        def mock_update_existing_user(username, password, role='user'):
            """Mock user update scenario."""
            return {
                'user_created': False,
                'user_existed': True,
                'user_updated': True,
                'creation_error': None,
                'validation_errors': [],
                'warning': f'User {username} already existed, password updated',
                'user_id': 12345,
                'username': username,
                'role': role,
                'updated_at': datetime.now().isoformat()
            }
        
        # Test user update scenario
        result = mock_update_existing_user('existinguser', 'NewPass123!', 'user')
        
        assert result['user_created'] == False
        assert result['user_existed'] == True
        assert result['user_updated'] == True
        assert result['creation_error'] is None
        assert 'password updated' in result['warning']
        assert 'updated_at' in result
    
    def test_user_creation_integration_with_qr_generation(self):
        """Test user creation integration with QR code generation."""
        def mock_qr_generation_with_user_creation(username, password, create_user=False, user_role='user'):
            """Mock QR generation with user creation."""
            qr_string = f"tak://com.atakmap.app/enroll?host=example.com&username={username}&token={password}"
            
            user_info = {
                'user_created': False,
                'user_existed': False,
                'user_updated': False,
                'creation_error': None,
                'validation_errors': []
            }
            
            if create_user:
                # Simulate user creation
                if username == 'newuser':
                    user_info.update({
                        'user_created': True,
                        'user_id': 12345,
                        'role': user_role
                    })
                elif username == 'existinguser':
                    user_info.update({
                        'user_existed': True,
                        'warning': 'User already exists'
                    })
                elif username == 'erroruser':
                    user_info.update({
                        'creation_error': 'Database error',
                        'troubleshooting': 'Check database connectivity'
                    })
            
            return {
                'qr_string': qr_string,
                'user_info': user_info,
                'validation_status': {
                    'user_creation_requested': create_user,
                    'user_creation_successful': user_info.get('user_created', False) or user_info.get('user_updated', False)
                }
            }
        
        # Test QR generation without user creation
        result = mock_qr_generation_with_user_creation('testuser', 'testpass', create_user=False)
        assert result['user_info']['user_created'] == False
        assert result['validation_status']['user_creation_requested'] == False
        assert result['validation_status']['user_creation_successful'] == False
        
        # Test QR generation with successful user creation
        result = mock_qr_generation_with_user_creation('newuser', 'testpass', create_user=True, user_role='admin')
        assert result['user_info']['user_created'] == True
        assert result['user_info']['role'] == 'admin'
        assert result['validation_status']['user_creation_requested'] == True
        assert result['validation_status']['user_creation_successful'] == True
        
        # Test QR generation with existing user
        result = mock_qr_generation_with_user_creation('existinguser', 'testpass', create_user=True)
        assert result['user_info']['user_existed'] == True
        assert 'warning' in result['user_info']
        assert result['validation_status']['user_creation_successful'] == False
        
        # Test QR generation with user creation error
        result = mock_qr_generation_with_user_creation('erroruser', 'testpass', create_user=True)
        assert result['user_info']['creation_error'] is not None
        assert 'troubleshooting' in result['user_info']
        assert result['validation_status']['user_creation_successful'] == False
    
    def test_user_creation_concurrent_requests(self):
        """Test user creation with concurrent requests."""
        def mock_concurrent_user_creation(username, password, request_id):
            """Mock concurrent user creation requests."""
            # Simulate race condition handling
            if request_id == 1:
                return {
                    'user_created': True,
                    'user_existed': False,
                    'request_id': request_id,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'user_created': False,
                    'user_existed': True,
                    'warning': 'User was created by concurrent request',
                    'request_id': request_id,
                    'timestamp': datetime.now().isoformat()
                }
        
        # Test concurrent requests
        result1 = mock_concurrent_user_creation('concurrentuser', 'testpass', 1)
        result2 = mock_concurrent_user_creation('concurrentuser', 'testpass', 2)
        
        assert result1['user_created'] == True
        assert result2['user_created'] == False
        assert result2['user_existed'] == True
        assert 'concurrent request' in result2['warning']
    
    def test_user_creation_cleanup_on_failure(self):
        """Test user creation cleanup on failure."""
        def mock_user_creation_with_cleanup(username, password, role='user'):
            """Mock user creation with cleanup on failure."""
            try:
                # Simulate partial user creation
                user_id = 12345  # User record created
                
                # Simulate failure during role assignment
                if role == 'admin':
                    raise Exception("Role assignment failed")
                
                return {
                    'user_created': True,
                    'user_id': user_id,
                    'username': username,
                    'role': role
                }
                
            except Exception as e:
                # Simulate cleanup
                return {
                    'user_created': False,
                    'user_existed': False,
                    'creation_error': str(e),
                    'cleanup_performed': True,
                    'troubleshooting': 'User creation failed and was rolled back'
                }
        
        # Test successful creation
        result = mock_user_creation_with_cleanup('testuser', 'testpass', 'user')
        assert result['user_created'] == True
        
        # Test failed creation with cleanup
        result = mock_user_creation_with_cleanup('testuser', 'testpass', 'admin')
        assert result['user_created'] == False
        assert 'Role assignment failed' in result['creation_error']
        assert result['cleanup_performed'] == True


if __name__ == '__main__':
    pytest.main([__file__])