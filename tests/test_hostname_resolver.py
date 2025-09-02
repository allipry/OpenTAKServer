"""
Unit tests for the hostname resolution service.
"""

import os
import pytest
import time
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import the module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from opentakserver.hostname_resolver import HostnameResolver, HostnameResult


class TestHostnameResolver:
    """Test cases for the HostnameResolver class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = HostnameResolver()
        # Clear any environment variables that might affect tests
        for env_var in ['EXTERNAL_HOST', 'SERVER_HOST', 'QR_DISABLE_EXTERNAL_IP', 'QR_HOST_DETECTION_TIMEOUT']:
            if env_var in os.environ:
                del os.environ[env_var]
    
    def teardown_method(self):
        """Clean up after tests."""
        # Clear cache
        self.resolver.clear_cache()
    
    def test_is_localhost_address(self):
        """Test localhost address detection."""
        # Test localhost patterns
        assert self.resolver.is_localhost_address('localhost') == True
        assert self.resolver.is_localhost_address('LOCALHOST') == True
        assert self.resolver.is_localhost_address('127.0.0.1') == True
        assert self.resolver.is_localhost_address('127.1.1.1') == True
        assert self.resolver.is_localhost_address('::1') == True
        assert self.resolver.is_localhost_address('0.0.0.0') == True
        
        # Test non-localhost addresses
        assert self.resolver.is_localhost_address('192.168.1.1') == False
        assert self.resolver.is_localhost_address('example.com') == False
        assert self.resolver.is_localhost_address('10.0.0.1') == False
        
        # Test edge cases
        assert self.resolver.is_localhost_address('') == True
        assert self.resolver.is_localhost_address(None) == True
        assert self.resolver.is_localhost_address('  localhost  ') == True
    
    def test_validate_hostname(self):
        """Test hostname validation."""
        # Valid hostnames
        valid, msg = self.resolver.validate_hostname('example.com')
        assert valid == True
        assert msg == ""
        
        valid, msg = self.resolver.validate_hostname('192.168.1.1')
        assert valid == True
        assert msg == ""
        
        valid, msg = self.resolver.validate_hostname('sub.example.com')
        assert valid == True
        assert msg == ""
        
        # Invalid hostnames
        valid, msg = self.resolver.validate_hostname('')
        assert valid == False
        assert "empty" in msg.lower()
        
        valid, msg = self.resolver.validate_hostname('invalid..hostname')
        assert valid == False
        
        valid, msg = self.resolver.validate_hostname('256.1.1.1')
        assert valid == False
        assert "invalid ip" in msg.lower()
        
        valid, msg = self.resolver.validate_hostname('hostname with spaces')
        assert valid == False
        assert "invalid characters" in msg.lower()
        
        # Test hostname too long
        long_hostname = 'a' * 254
        valid, msg = self.resolver.validate_hostname(long_hostname)
        assert valid == False
        assert "too long" in msg.lower()
    
    def test_override_hostname_priority(self):
        """Test that override hostname has highest priority."""
        result = self.resolver.get_external_hostname(
            request_host='localhost:8080',
            override_host='override.example.com'
        )
        
        assert result.hostname == 'override.example.com'
        assert result.detection_method == 'override'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
        assert len(result.warnings) == 0
    
    def test_override_hostname_localhost_warning(self):
        """Test warning when override hostname is localhost."""
        result = self.resolver.get_external_hostname(
            override_host='localhost'
        )
        
        assert result.hostname == 'localhost'
        assert result.detection_method == 'override'
        assert result.is_localhost == True
        assert result.is_external_accessible == False
        assert any('localhost' in warning for warning in result.warnings)
    
    def test_override_hostname_invalid_warning(self):
        """Test warning when override hostname is invalid."""
        result = self.resolver.get_external_hostname(
            override_host='invalid..hostname'
        )
        
        assert result.hostname == 'invalid..hostname'
        assert result.detection_method == 'override'
        assert any('validation failed' in warning for warning in result.warnings)
    
    @patch.dict(os.environ, {'EXTERNAL_HOST': 'env.example.com'})
    def test_environment_variable_priority(self):
        """Test that environment variables have second priority."""
        resolver = HostnameResolver()  # Create new instance to pick up env vars
        
        result = resolver.get_external_hostname(request_host='localhost:8080')
        
        assert result.hostname == 'env.example.com'
        assert result.detection_method == 'env_var'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
    
    @patch.dict(os.environ, {'SERVER_HOST': 'server.example.com'})
    def test_server_host_environment_variable(self):
        """Test SERVER_HOST environment variable fallback."""
        resolver = HostnameResolver()
        
        result = resolver.get_external_hostname(request_host='localhost:8080')
        
        assert result.hostname == 'server.example.com'
        assert result.detection_method == 'env_var'
    
    @patch.dict(os.environ, {'EXTERNAL_HOST': 'external.com', 'SERVER_HOST': 'server.com'})
    def test_external_host_priority_over_server_host(self):
        """Test that EXTERNAL_HOST takes priority over SERVER_HOST."""
        resolver = HostnameResolver()
        
        result = resolver.get_external_hostname()
        
        assert result.hostname == 'external.com'
        assert result.detection_method == 'env_var'
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_ip_detection(self, mock_get):
        """Test external IP detection."""
        # Mock successful response
        mock_response = Mock()
        mock_response.text = '203.0.113.1'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.resolver.get_external_hostname()
        
        assert result.hostname == '203.0.113.1'
        assert result.detection_method == 'external_ip'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_ip_detection_httpbin_format(self, mock_get):
        """Test external IP detection with httpbin JSON format."""
        # Mock httpbin.org response format
        mock_response = Mock()
        mock_response.json.return_value = {'origin': '203.0.113.1'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock the service URL to trigger JSON parsing
        with patch.object(self.resolver, 'EXTERNAL_IP_SERVICES', ['https://httpbin.org/ip']):
            result = self.resolver.get_external_hostname()
        
        assert result.hostname == '203.0.113.1'
        assert result.detection_method == 'external_ip'
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_ip_detection_fallback_services(self, mock_get):
        """Test external IP detection with service fallback."""
        # First service fails, second succeeds
        def side_effect(url, timeout):
            if 'ipify' in url:
                raise Exception("Service unavailable")
            else:
                mock_response = Mock()
                mock_response.text = '203.0.113.1'
                mock_response.raise_for_status.return_value = None
                return mock_response
        
        mock_get.side_effect = side_effect
        
        result = self.resolver.get_external_hostname()
        
        assert result.hostname == '203.0.113.1'
        assert result.detection_method == 'external_ip'
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_ip_detection_all_services_fail(self, mock_get):
        """Test external IP detection when all services fail."""
        mock_get.side_effect = Exception("All services unavailable")
        
        result = self.resolver.get_external_hostname(request_host='example.com:8080')
        
        # Should fall back to request host
        assert result.hostname == 'example.com'
        assert result.detection_method == 'request_host'
        assert any('External IP detection failed' in warning for warning in result.warnings)
    
    def test_request_host_priority(self):
        """Test request host is used when not localhost."""
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='example.com:8080')
        
        assert result.hostname == 'example.com'
        assert result.detection_method == 'request_host'
        assert result.is_localhost == False
        assert result.is_external_accessible == True
    
    def test_request_host_localhost_skipped(self):
        """Test request host is skipped when it's localhost."""
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='localhost:8080')
        
        # Should fall back since localhost is not suitable
        assert result.hostname == 'localhost'
        assert result.detection_method == 'fallback'
        assert any('localhost' in warning for warning in result.warnings)
    
    def test_fallback_behavior(self):
        """Test fallback behavior when all other methods fail."""
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='localhost:8080')
        
        assert result.hostname == 'localhost'
        assert result.detection_method == 'fallback'
        assert result.is_localhost == True
        assert result.is_external_accessible == False
        assert any('fallback hostname' in warning for warning in result.warnings)
        assert any('EXTERNAL_HOST' in warning for warning in result.warnings)
    
    @patch.dict(os.environ, {'QR_DISABLE_EXTERNAL_IP': 'true'})
    def test_external_ip_disabled(self):
        """Test external IP detection can be disabled."""
        resolver = HostnameResolver()
        
        result = resolver.get_external_hostname(request_host='example.com:8080')
        
        # Should skip external IP and use request host
        assert result.hostname == 'example.com'
        assert result.detection_method == 'request_host'
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_ip_caching(self, mock_get):
        """Test external IP caching functionality."""
        # Mock successful response
        mock_response = Mock()
        mock_response.text = '203.0.113.1'
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # First call should make HTTP request
        ip1 = self.resolver.get_external_ip()
        assert ip1 == '203.0.113.1'
        assert mock_get.call_count == 1
        
        # Second call should use cache
        ip2 = self.resolver.get_external_ip()
        assert ip2 == '203.0.113.1'
        assert mock_get.call_count == 1  # No additional calls
    
    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        # Set very short cache timeout
        self.resolver._cache_timeout = 1
        
        with patch('opentakserver.hostname_resolver.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = '203.0.113.1'
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # First call
            ip1 = self.resolver.get_external_ip()
            assert ip1 == '203.0.113.1'
            assert mock_get.call_count == 1
            
            # Wait for cache to expire
            time.sleep(1.1)
            
            # Second call should make new HTTP request
            ip2 = self.resolver.get_external_ip()
            assert ip2 == '203.0.113.1'
            assert mock_get.call_count == 2
    
    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Set up cache
        self.resolver._external_ip_cache = {
            'ip': '203.0.113.1',
            'timestamp': datetime.now(),
            'service': 'test'
        }
        
        # Clear cache
        self.resolver.clear_cache()
        
        assert self.resolver._external_ip_cache is None
    
    def test_is_valid_ip(self):
        """Test IP address validation."""
        # Valid IPs
        assert self.resolver._is_valid_ip('192.168.1.1') == True
        assert self.resolver._is_valid_ip('203.0.113.1') == True
        assert self.resolver._is_valid_ip('0.0.0.0') == True
        assert self.resolver._is_valid_ip('255.255.255.255') == True
        
        # Invalid IPs
        assert self.resolver._is_valid_ip('256.1.1.1') == False
        assert self.resolver._is_valid_ip('192.168.1') == False
        assert self.resolver._is_valid_ip('192.168.1.1.1') == False
        assert self.resolver._is_valid_ip('not.an.ip') == False
        assert self.resolver._is_valid_ip('') == False
        assert self.resolver._is_valid_ip(None) == False
    
    @patch.dict(os.environ, {'QR_HOST_DETECTION_TIMEOUT': '10'})
    def test_timeout_configuration(self):
        """Test timeout configuration from environment."""
        resolver = HostnameResolver()
        assert resolver._request_timeout == 10
        assert resolver._cache_timeout == 10
    
    def test_hostname_result_structure(self):
        """Test HostnameResult structure and fields."""
        result = self.resolver.get_external_hostname(override_host='test.example.com')
        
        assert hasattr(result, 'hostname')
        assert hasattr(result, 'detection_method')
        assert hasattr(result, 'is_localhost')
        assert hasattr(result, 'is_external_accessible')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'timestamp')
        
        assert isinstance(result.hostname, str)
        assert isinstance(result.detection_method, str)
        assert isinstance(result.is_localhost, bool)
        assert isinstance(result.is_external_accessible, bool)
        assert isinstance(result.warnings, list)
        assert isinstance(result.timestamp, datetime)


if __name__ == '__main__':
    pytest.main([__file__])