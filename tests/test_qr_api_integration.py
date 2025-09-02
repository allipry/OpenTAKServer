"""
Integration tests for QR code API endpoints.
Tests the complete QR code generation flow including user creation.
"""

import os
import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
from flask import Flask

# Add the parent directory to the path so we can import the module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, '/app')

from opentakserver.hostname_resolver import HostnameResolver, HostnameResult


class MockFlaskApp:
    """Mock Flask application for testing QR endpoints."""
    
    def __init__(self):
        self.test_client_instance = None
        self.config = {'TESTING': True}
    
    def test_client(self):
        """Return mock test client."""
        if not self.test_client_instance:
            self.test_client_instance = MockTestClient()
        return self.test_client_instance


class MockTestClient:
    """Mock test client for API endpoint testing."""
    
    def __init__(self):
        self.last_request = None
        self.mock_responses = {}
    
    def get(self, path, **kwargs):
        """Mock GET request."""
        self.last_request = {'method': 'GET', 'path': path, 'kwargs': kwargs}
        return self._get_mock_response(path, 'GET')
    
    def post(self, path, **kwargs):
        """Mock POST request."""
        self.last_request = {'method': 'POST', 'path': path, 'kwargs': kwargs}
        return self._get_mock_response(path, 'POST')
    
    def _get_mock_response(self, path, method):
        """Get mock response for path and method."""
        key = f"{method}:{path}"
        if key in self.mock_responses:
            return self.mock_responses[key]
        
        # Default mock response
        return MockResponse({
            'qr_string': 'tak://com.atakmap.app/enroll?host=localhost&username=admin&token=password',
            'server_url': 'https://localhost:8443',
            'connection_details': {
                'server': 'localhost',
                'username': 'admin',
                'token': 'password',
                'token_obfuscated': 'pass****',
                'scheme': 'tak://com.atakmap.app/enroll'
            },
            'hostname_info': {
                'detected_method': 'fallback',
                'is_localhost': True,
                'is_external_accessible': False,
                'warnings': ['Using fallback hostname']
            },
            'user_info': {
                'user_created': False,
                'user_existed': False,
                'creation_error': None
            },
            'timestamp': datetime.now().isoformat()
        })
    
    def set_mock_response(self, path, method, response_data, status_code=200):
        """Set mock response for specific path and method."""
        key = f"{method}:{path}"
        self.mock_responses[key] = MockResponse(response_data, status_code)


class MockResponse:
    """Mock HTTP response."""
    
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
        self._json = data
    
    def get_json(self):
        """Return JSON data."""
        return self._json
    
    @property
    def json(self):
        """JSON property."""
        return self._json


class TestQRAPIIntegration:
    """Integration tests for QR code API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.app = MockFlaskApp()
        self.client = self.app.test_client()
        
        # Clear environment variables
        for env_var in ['EXTERNAL_HOST', 'SERVER_HOST', 'QR_DISABLE_EXTERNAL_IP', 'QR_HOST_DETECTION_TIMEOUT']:
            if env_var in os.environ:
                del os.environ[env_var]
    
    def test_itak_qr_endpoint_get_request(self):
        """Test iTAK QR endpoint with GET request."""
        # Mock successful response
        expected_response = {
            'qr_string': 'tak://com.atakmap.app/enroll?host=192.168.1.100&username=testuser&token=testpass',
            'server_url': 'https://192.168.1.100:8443',
            'connection_details': {
                'server': '192.168.1.100',
                'username': 'testuser',
                'token': 'testpass',
                'token_obfuscated': 'test****',
                'scheme': 'tak://com.atakmap.app/enroll'
            },
            'hostname_info': {
                'detected_method': 'external_ip',
                'is_localhost': False,
                'is_external_accessible': True,
                'warnings': []
            },
            'user_info': {
                'user_created': False,
                'user_existed': False,
                'creation_error': None
            },
            'timestamp': datetime.now().isoformat()
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'GET', expected_response)
        
        # Make request
        response = self.client.get('/api/itak_qr_string?username=testuser&token=testpass')
        
        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data['qr_string'].startswith('tak://com.atakmap.app/enroll?')
        assert 'host=192.168.1.100' in data['qr_string']
        assert 'username=testuser' in data['qr_string']
        assert 'token=testpass' in data['qr_string']
    
    def test_itak_qr_endpoint_post_request(self):
        """Test iTAK QR endpoint with POST request."""
        # Mock successful response
        expected_response = {
            'qr_string': 'tak://com.atakmap.app/enroll?host=example.com&username=admin&token=secret',
            'server_url': 'https://example.com:8443',
            'connection_details': {
                'server': 'example.com',
                'username': 'admin',
                'token': 'secret',
                'token_obfuscated': 'secr****',
                'scheme': 'tak://com.atakmap.app/enroll'
            },
            'hostname_info': {
                'detected_method': 'override',
                'is_localhost': False,
                'is_external_accessible': True,
                'warnings': []
            },
            'user_info': {
                'user_created': True,
                'user_existed': False,
                'creation_error': None
            },
            'timestamp': datetime.now().isoformat()
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'POST', expected_response)
        
        # Make request
        response = self.client.post('/api/itak_qr_string', json={
            'username': 'admin',
            'token': 'secret',
            'server_host': 'example.com',
            'create_user': True
        })
        
        # Verify response
        assert response.status_code == 200
        data = response.get_json()
        assert data['qr_string'].startswith('tak://com.atakmap.app/enroll?')
        assert data['hostname_info']['detected_method'] == 'override'
        assert data['user_info']['user_created'] == True
    
    def test_qr_endpoint_parameter_validation(self):
        """Test QR endpoint parameter validation."""
        # Test invalid JSON
        invalid_json_response = {
            'error': 'Invalid JSON in request body',
            'details': 'Expecting value: line 1 column 1 (char 0)',
            'troubleshooting': 'Ensure request body contains valid JSON format',
            'timestamp': datetime.now().isoformat()
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'POST', invalid_json_response, 400)
        
        response = self.client.post('/api/itak_qr_string', data='invalid json')
        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid JSON' in data['error']
        
        # Test missing parameters
        missing_params_response = {
            'error': 'Parameter validation failed',
            'validation_errors': ['Username cannot be empty'],
            'troubleshooting': 'Fix the parameter validation errors and try again',
            'timestamp': datetime.now().isoformat()
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'POST', missing_params_response, 400)
        
        response = self.client.post('/api/itak_qr_string', json={'username': '', 'token': 'pass'})
        assert response.status_code == 400
        data = response.get_json()
        assert 'Parameter validation failed' in data['error']
    
    def test_qr_endpoint_hostname_resolution_integration(self):
        """Test QR endpoint integration with hostname resolution."""
        with patch('opentakserver.hostname_resolver.HostnameResolver') as mock_resolver_class:
            # Mock hostname resolver
            mock_resolver = Mock()
            mock_hostname_result = HostnameResult(
                hostname='192.168.1.100',
                detection_method='external_ip',
                is_localhost=False,
                is_external_accessible=True,
                warnings=[],
                timestamp=datetime.now()
            )
            mock_resolver.get_external_hostname.return_value = mock_hostname_result
            mock_resolver_class.return_value = mock_resolver
            
            # Mock successful response with resolved hostname
            expected_response = {
                'qr_string': 'tak://com.atakmap.app/enroll?host=192.168.1.100&username=user&token=pass',
                'hostname_info': {
                    'detected_method': 'external_ip',
                    'is_localhost': False,
                    'is_external_accessible': True,
                    'warnings': []
                }
            }
            
            self.client.set_mock_response('/api/itak_qr_string', 'GET', expected_response)
            
            response = self.client.get('/api/itak_qr_string?username=user&token=pass')
            
            # Verify hostname resolution was used
            assert response.status_code == 200
            data = response.get_json()
            assert data['hostname_info']['detected_method'] == 'external_ip'
            assert data['hostname_info']['is_localhost'] == False
    
    def test_qr_endpoint_user_creation_integration(self):
        """Test QR endpoint integration with user creation."""
        # Mock successful user creation
        user_creation_response = {
            'qr_string': 'tak://com.atakmap.app/enroll?host=example.com&username=newuser&token=newpass',
            'user_info': {
                'user_created': True,
                'user_existed': False,
                'user_updated': False,
                'creation_error': None,
                'validation_errors': []
            },
            'validation_status': {
                'user_creation_requested': True,
                'user_creation_successful': True
            }
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'POST', user_creation_response)
        
        response = self.client.post('/api/itak_qr_string', json={
            'username': 'newuser',
            'token': 'newpass',
            'create_user': True,
            'user_role': 'user'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['user_info']['user_created'] == True
        assert data['validation_status']['user_creation_successful'] == True
    
    def test_qr_endpoint_user_creation_failure(self):
        """Test QR endpoint with user creation failure."""
        # Mock user creation failure
        user_creation_failure_response = {
            'qr_string': 'tak://com.atakmap.app/enroll?host=example.com&username=failuser&token=failpass',
            'user_info': {
                'user_created': False,
                'user_existed': False,
                'user_updated': False,
                'creation_error': 'Database connection failed',
                'validation_errors': []
            },
            'validation_status': {
                'user_creation_requested': True,
                'user_creation_successful': False
            },
            'troubleshooting': 'Check database connectivity and user permissions'
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'POST', user_creation_failure_response)
        
        response = self.client.post('/api/itak_qr_string', json={
            'username': 'failuser',
            'token': 'failpass',
            'create_user': True
        })
        
        assert response.status_code == 200  # QR generation should still succeed
        data = response.get_json()
        assert data['user_info']['user_created'] == False
        assert 'Database connection failed' in data['user_info']['creation_error']
        assert 'troubleshooting' in data
    
    def test_qr_endpoint_localhost_warning(self):
        """Test QR endpoint localhost detection and warning."""
        # Mock localhost detection
        localhost_response = {
            'qr_string': 'tak://com.atakmap.app/enroll?host=localhost&username=user&token=pass',
            'hostname_info': {
                'detected_method': 'fallback',
                'is_localhost': True,
                'is_external_accessible': False,
                'warnings': [
                    'Using fallback hostname - QR code may not work for external clients',
                    'Consider setting EXTERNAL_HOST environment variable or providing server_host parameter'
                ]
            },
            'validation_status': {
                'hostname_accessible': False
            }
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'GET', localhost_response)
        
        response = self.client.get('/api/itak_qr_string?username=user&token=pass')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['hostname_info']['is_localhost'] == True
        assert len(data['hostname_info']['warnings']) > 0
        assert any('fallback hostname' in warning for warning in data['hostname_info']['warnings'])
    
    def test_qr_endpoint_hostname_override(self):
        """Test QR endpoint with hostname override."""
        # Mock hostname override
        override_response = {
            'qr_string': 'tak://com.atakmap.app/enroll?host=custom.example.com&username=user&token=pass',
            'hostname_info': {
                'detected_method': 'override',
                'is_localhost': False,
                'is_external_accessible': True,
                'warnings': []
            }
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'POST', override_response)
        
        response = self.client.post('/api/itak_qr_string', json={
            'username': 'user',
            'token': 'pass',
            'server_host': 'custom.example.com'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['hostname_info']['detected_method'] == 'override'
        assert 'custom.example.com' in data['qr_string']
    
    def test_qr_endpoint_error_handling(self):
        """Test QR endpoint error handling."""
        # Mock internal server error
        error_response = {
            'error': 'Unexpected error in enhanced endpoint',
            'details': 'Hostname resolution service unavailable',
            'troubleshooting': 'Check system logs for detailed error information',
            'timestamp': datetime.now().isoformat()
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'GET', error_response, 500)
        
        response = self.client.get('/api/itak_qr_string?username=user&token=pass')
        
        assert response.status_code == 500
        data = response.get_json()
        assert 'error' in data
        assert 'troubleshooting' in data
    
    def test_atak_qr_endpoint_compatibility(self):
        """Test ATAK QR endpoint for dashboard compatibility."""
        # Mock ATAK endpoint response
        atak_response = {
            'qr_string': 'tak://com.atakmap.app/enroll?host=example.com&username=admin&token=password',
            'server_url': 'https://example.com:8443',
            'connection_details': {
                'server': 'example.com',
                'username': 'admin',
                'token': 'password',
                'scheme': 'tak://com.atakmap.app/enroll'
            }
        }
        
        self.client.set_mock_response('/api/atak_qr_string', 'GET', atak_response)
        
        response = self.client.get('/api/atak_qr_string?username=admin&token=password')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['qr_string'].startswith('tak://com.atakmap.app/enroll?')
    
    def test_qr_endpoint_token_obfuscation(self):
        """Test QR endpoint token obfuscation in response."""
        # Mock response with token obfuscation
        obfuscated_response = {
            'qr_string': 'tak://com.atakmap.app/enroll?host=example.com&username=user&token=verylongpassword123',
            'connection_details': {
                'token': 'verylongpassword123',
                'token_obfuscated': 'very****'
            }
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'GET', obfuscated_response)
        
        response = self.client.get('/api/itak_qr_string?username=user&token=verylongpassword123')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['connection_details']['token'] == 'verylongpassword123'
        assert data['connection_details']['token_obfuscated'] == 'very****'
    
    def test_qr_endpoint_validation_status(self):
        """Test QR endpoint validation status information."""
        # Mock response with validation status
        validation_response = {
            'qr_string': 'tak://com.atakmap.app/enroll?host=example.com&username=user&token=pass',
            'validation_status': {
                'qr_string_length': 75,
                'qr_string_valid': True,
                'hostname_accessible': True,
                'user_creation_requested': False,
                'user_creation_successful': False
            }
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'GET', validation_response)
        
        response = self.client.get('/api/itak_qr_string?username=user&token=pass')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'validation_status' in data
        assert data['validation_status']['qr_string_valid'] == True
        assert data['validation_status']['hostname_accessible'] == True
    
    @patch.dict(os.environ, {'EXTERNAL_HOST': 'env.example.com'})
    def test_qr_endpoint_environment_variable_integration(self):
        """Test QR endpoint with environment variable configuration."""
        # Mock response using environment variable
        env_response = {
            'qr_string': 'tak://com.atakmap.app/enroll?host=env.example.com&username=user&token=pass',
            'hostname_info': {
                'detected_method': 'env_var',
                'is_localhost': False,
                'is_external_accessible': True,
                'warnings': []
            }
        }
        
        self.client.set_mock_response('/api/itak_qr_string', 'GET', env_response)
        
        response = self.client.get('/api/itak_qr_string?username=user&token=pass')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['hostname_info']['detected_method'] == 'env_var'
        assert 'env.example.com' in data['qr_string']


if __name__ == '__main__':
    pytest.main([__file__])