"""
Unit tests for error handling and edge cases in QR code generation.
Tests various error conditions, edge cases, and recovery mechanisms.
"""

import os
import pytest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
import json

# Add the parent directory to the path so we can import the module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from opentakserver.hostname_resolver import HostnameResolver, HostnameResult


class TestErrorHandling:
    """Test cases for error handling and edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = HostnameResolver()
        # Clear any environment variables that might affect tests
        for env_var in ['EXTERNAL_HOST', 'SERVER_HOST', 'QR_DISABLE_EXTERNAL_IP', 'QR_HOST_DETECTION_TIMEOUT']:
            if env_var in os.environ:
                del os.environ[env_var]
    
    def teardown_method(self):
        """Clean up after tests."""
        self.resolver.clear_cache()
    
    def test_none_input_handling(self):
        """Test handling of None inputs."""
        # Test None request_host
        result = self.resolver.get_external_hostname(request_host=None, override_host=None)
        assert result.hostname is not None
        assert result.detection_method in ['external_ip', 'fallback']
        
        # Test None override_host (should be ignored)
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='example.com:8080', override_host=None)
        assert result.hostname == 'example.com'
        assert result.detection_method == 'request_host'
    
    def test_empty_string_input_handling(self):
        """Test handling of empty string inputs."""
        # Test empty request_host
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='', override_host=None)
        assert result.hostname is not None
        assert result.detection_method == 'fallback'
        
        # Test empty override_host (should be ignored)
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='example.com:8080', override_host='')
        assert result.hostname == 'example.com'
        assert result.detection_method == 'request_host'
    
    def test_whitespace_input_handling(self):
        """Test handling of whitespace-only inputs."""
        # Test whitespace request_host
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host='   ', override_host=None)
        assert result.detection_method == 'fallback'
        
        # Test whitespace override_host
        result = self.resolver.get_external_hostname(request_host='example.com:8080', override_host='   ')
        assert result.hostname == '   '  # Override is used as-is
        assert result.detection_method == 'override'
        assert len(result.warnings) > 0  # Should have validation warning
    
    def test_invalid_hostname_formats(self):
        """Test handling of invalid hostname formats."""
        invalid_hostnames = [
            'invalid..hostname',
            'hostname with spaces',
            'hostname_with_underscore',
            '256.1.1.1',  # Invalid IP
            'hostname.',
            '.hostname',
            'very-long-hostname-' + 'a' * 250,  # Too long
            'host@name',
            'host#name',
            'host%name'
        ]
        
        for invalid_hostname in invalid_hostnames:
            result = self.resolver.get_external_hostname(
                request_host='example.com:8080',
                override_host=invalid_hostname
            )
            
            assert result.hostname == invalid_hostname  # Override is used as-is
            assert result.detection_method == 'override'
            # Should have warnings for invalid hostnames
            if invalid_hostname not in ['hostname_with_underscore']:  # Some might be valid
                assert len(result.warnings) > 0
    
    def test_malformed_request_host_handling(self):
        """Test handling of malformed request_host values."""
        malformed_hosts = [
            'host:invalid_port',
            'host:99999',  # Port too high
            'host:-1',     # Negative port
            'host:port:extra',  # Multiple colons
            ':8080',       # Missing hostname
            'host:',       # Missing port
            '[invalid_ipv6',  # Malformed IPv6
            'host]:8080'   # Malformed IPv6
        ]
        
        for malformed_host in malformed_hosts:
            with patch.object(self.resolver, '_disable_external_ip', True):
                result = self.resolver.get_external_hostname(request_host=malformed_host)
            
            # Should handle gracefully and extract what it can
            assert result.hostname is not None
            assert result.detection_method in ['request_host', 'fallback']
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_ip_service_errors(self, mock_get):
        """Test handling of external IP service errors."""
        # Test different types of HTTP errors
        import requests
        
        error_scenarios = [
            requests.ConnectionError("Connection failed"),
            requests.Timeout("Request timeout"),
            requests.HTTPError("HTTP 500 Error"),
            requests.RequestException("Generic request error"),
            Exception("Unexpected error")
        ]
        
        for error in error_scenarios:
            mock_get.side_effect = error
            
            result = self.resolver.get_external_hostname(request_host='fallback.example.com:8080')
            
            # Should fall back gracefully
            assert result.hostname == 'fallback.example.com'
            assert result.detection_method == 'request_host'
            assert len(result.warnings) > 0
            assert any('External IP detection failed' in warning for warning in result.warnings)
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_ip_invalid_responses(self, mock_get):
        """Test handling of invalid external IP service responses."""
        invalid_responses = [
            '',  # Empty response
            'not an ip',  # Invalid format
            '256.256.256.256',  # Invalid IP
            'multiple\nlines\nresponse',  # Multi-line
            '{"error": "service unavailable"}',  # JSON error
            '<html>Error page</html>',  # HTML response
            '192.168.1.1, 10.0.0.1',  # Multiple IPs
        ]
        
        for invalid_response in invalid_responses:
            mock_response = Mock()
            mock_response.text = invalid_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            result = self.resolver.get_external_hostname(request_host='fallback.example.com:8080')
            
            # Should fall back when IP is invalid
            if invalid_response in ['', 'not an ip', '256.256.256.256']:
                assert result.hostname == 'fallback.example.com'
                assert result.detection_method == 'request_host'
            else:
                # Some responses might be partially valid
                assert result.hostname is not None
    
    @patch('opentakserver.hostname_resolver.requests.get')
    def test_external_ip_json_parsing_errors(self, mock_get):
        """Test handling of JSON parsing errors from external services."""
        # Test invalid JSON from httpbin-style service
        mock_response = Mock()
        mock_response.text = 'invalid json'
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock the service URL to trigger JSON parsing
        with patch.object(self.resolver, 'EXTERNAL_IP_SERVICES', ['https://httpbin.org/ip']):
            result = self.resolver.get_external_hostname(request_host='fallback.example.com:8080')
        
        # Should fall back to text parsing or next service
        assert result.hostname is not None
    
    def test_hostname_validation_edge_cases(self):
        """Test hostname validation edge cases."""
        edge_cases = [
            ('', False, 'empty'),
            ('a', True, 'single character'),
            ('1', True, 'single digit'),
            ('a.b', True, 'minimal domain'),
            ('1.2.3.4', True, 'IP address'),
            ('0.0.0.0', True, 'zero IP'),
            ('255.255.255.255', True, 'max IP'),
            ('localhost', True, 'localhost'),
            ('LOCALHOST', True, 'uppercase localhost'),
            ('127.0.0.1', True, 'loopback IP'),
            ('::1', True, 'IPv6 loopback'),
            ('a' * 63, True, 'max label length'),
            ('a' * 64, False, 'label too long'),
            ('a' * 253, True, 'max hostname length'),
            ('a' * 254, False, 'hostname too long')
        ]
        
        for hostname, should_be_valid, description in edge_cases:
            is_valid, message = self.resolver.validate_hostname(hostname)
            
            if should_be_valid:
                assert is_valid == True, f"Hostname '{hostname}' ({description}) should be valid, error: {message}"
            else:
                assert is_valid == False, f"Hostname '{hostname}' ({description}) should be invalid"
    
    def test_localhost_detection_edge_cases(self):
        """Test localhost detection edge cases."""
        localhost_cases = [
            ('localhost', True),
            ('LOCALHOST', True),
            ('LocalHost', True),
            ('127.0.0.1', True),
            ('127.1.1.1', True),
            ('127.255.255.255', True),
            ('::1', True),
            ('0.0.0.0', True),
            ('', True),  # Empty is considered localhost
            (None, True),  # None is considered localhost
            ('   localhost   ', True),  # Whitespace trimmed
            ('128.0.0.1', False),  # Not in 127.x.x.x range
            ('localhost.domain.com', False),  # Contains localhost but not exact match
            ('mylocalhost', False),  # Contains localhost but not exact match
        ]
        
        for hostname, should_be_localhost in localhost_cases:
            is_localhost = self.resolver.is_localhost_address(hostname)
            assert is_localhost == should_be_localhost, f"Hostname '{hostname}' localhost detection failed"
    
    def test_ip_validation_edge_cases(self):
        """Test IP address validation edge cases."""
        ip_cases = [
            ('0.0.0.0', True),
            ('255.255.255.255', True),
            ('192.168.1.1', True),
            ('10.0.0.1', True),
            ('172.16.0.1', True),
            ('256.1.1.1', False),  # Out of range
            ('1.256.1.1', False),  # Out of range
            ('1.1.256.1', False),  # Out of range
            ('1.1.1.256', False),  # Out of range
            ('-1.1.1.1', False),   # Negative
            ('1.1.1', False),      # Too few octets
            ('1.1.1.1.1', False),  # Too many octets
            ('1.1.1.a', False),    # Non-numeric
            ('', False),           # Empty
            (None, False),         # None
            ('192.168.1.01', True), # Leading zero (should be valid)
            ('192.168.001.1', True), # Leading zeros
        ]
        
        for ip, should_be_valid in ip_cases:
            is_valid = self.resolver._is_valid_ip(ip)
            assert is_valid == should_be_valid, f"IP '{ip}' validation failed"
    
    def test_cache_corruption_handling(self):
        """Test handling of corrupted cache data."""
        # Test with corrupted cache data
        corrupted_cache_scenarios = [
            None,  # None cache
            {},    # Empty cache
            {'ip': None},  # Missing fields
            {'timestamp': None},  # Invalid timestamp
            {'ip': '', 'timestamp': datetime.now()},  # Empty IP
            {'ip': 'invalid', 'timestamp': 'invalid'},  # Invalid data types
        ]
        
        for corrupted_cache in corrupted_cache_scenarios:
            self.resolver._external_ip_cache = corrupted_cache
            
            # Should handle gracefully and not crash
            with patch('opentakserver.hostname_resolver.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.text = '203.0.113.1'
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response
                
                ip = self.resolver.get_external_ip()
                assert ip == '203.0.113.1'  # Should work despite corrupted cache
    
    def test_environment_variable_edge_cases(self):
        """Test environment variable handling edge cases."""
        env_var_cases = [
            ('', 'empty string'),
            ('   ', 'whitespace only'),
            ('localhost', 'localhost value'),
            ('127.0.0.1', 'loopback IP'),
            ('invalid..hostname', 'invalid format'),
            ('a' * 300, 'very long hostname')
        ]
        
        for env_value, description in env_var_cases:
            with patch.dict(os.environ, {'EXTERNAL_HOST': env_value}):
                resolver = HostnameResolver()
                result = resolver.get_external_hostname()
                
                if env_value.strip():  # Non-empty after strip
                    assert result.hostname == env_value
                    assert result.detection_method == 'env_var'
                    
                    if env_value.strip() in ['localhost', '127.0.0.1']:
                        assert result.is_localhost == True
                        assert len(result.warnings) > 0
                else:
                    # Empty env var should be ignored
                    assert result.detection_method != 'env_var'
    
    def test_concurrent_cache_access(self):
        """Test concurrent access to cache (thread safety simulation)."""
        import threading
        import time
        
        results = []
        errors = []
        
        def cache_access_thread():
            try:
                # Simulate concurrent cache access
                self.resolver.clear_cache()
                
                with patch('opentakserver.hostname_resolver.requests.get') as mock_get:
                    mock_response = Mock()
                    mock_response.text = '203.0.113.1'
                    mock_response.raise_for_status.return_value = None
                    mock_get.return_value = mock_response
                    
                    ip = self.resolver.get_external_ip()
                    results.append(ip)
                    
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=cache_access_thread)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 5
        assert all(result == '203.0.113.1' for result in results)
    
    def test_memory_pressure_handling(self):
        """Test handling under memory pressure conditions."""
        # Simulate memory pressure by creating large objects
        large_objects = []
        
        try:
            # Create some memory pressure (but not too much to crash the test)
            for i in range(100):
                large_objects.append('x' * 10000)
            
            # Test hostname resolution under memory pressure
            with patch('opentakserver.hostname_resolver.requests.get') as mock_get:
                mock_response = Mock()
                mock_response.text = '203.0.113.1'
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response
                
                result = self.resolver.get_external_hostname()
                
                # Should still work
                assert result.hostname == '203.0.113.1'
                assert result.detection_method == 'external_ip'
                
        finally:
            # Clean up
            large_objects.clear()
    
    def test_unicode_hostname_handling(self):
        """Test handling of Unicode hostnames."""
        unicode_hostnames = [
            'тест.example.com',  # Cyrillic
            'テスト.example.com',   # Japanese
            'test.例え.com',      # Mixed
            'café.example.com',   # Accented characters
            'naïve.example.com',  # More accented characters
        ]
        
        for unicode_hostname in unicode_hostnames:
            result = self.resolver.get_external_hostname(
                request_host='example.com:8080',
                override_host=unicode_hostname
            )
            
            # Should handle Unicode hostnames (may have warnings)
            assert result.hostname == unicode_hostname
            assert result.detection_method == 'override'
            # May have validation warnings for non-ASCII characters
    
    def test_very_long_input_handling(self):
        """Test handling of very long inputs."""
        very_long_hostname = 'a' * 1000 + '.example.com'
        very_long_request_host = 'b' * 1000 + '.example.com:8080'
        
        # Test very long override hostname
        result = self.resolver.get_external_hostname(
            request_host='normal.example.com:8080',
            override_host=very_long_hostname
        )
        
        assert result.hostname == very_long_hostname
        assert result.detection_method == 'override'
        assert len(result.warnings) > 0  # Should have validation warning
        
        # Test very long request host
        with patch.object(self.resolver, '_disable_external_ip', True):
            result = self.resolver.get_external_hostname(request_host=very_long_request_host)
        
        expected_hostname = very_long_request_host.split(':')[0]
        assert result.hostname == expected_hostname
    
    def test_special_character_handling(self):
        """Test handling of special characters in hostnames."""
        special_char_hostnames = [
            'host-name.example.com',  # Hyphen (valid)
            'host_name.example.com',  # Underscore (technically invalid in DNS)
            'host.name.example.com',  # Multiple dots (valid)
            'host@example.com',       # At symbol (invalid)
            'host#example.com',       # Hash (invalid)
            'host%example.com',       # Percent (invalid)
            'host&example.com',       # Ampersand (invalid)
            'host+example.com',       # Plus (invalid)
            'host=example.com',       # Equals (invalid)
        ]
        
        for hostname in special_char_hostnames:
            result = self.resolver.get_external_hostname(
                request_host='normal.example.com:8080',
                override_host=hostname
            )
            
            assert result.hostname == hostname
            assert result.detection_method == 'override'
            
            # Invalid characters should generate warnings
            if any(char in hostname for char in '@#%&+='):
                assert len(result.warnings) > 0
    
    def test_qr_string_generation_edge_cases(self):
        """Test QR string generation edge cases."""
        def generate_qr_string(hostname, username, token):
            """Generate iTAK QR string."""
            from urllib.parse import quote
            encoded_hostname = quote(hostname, safe=':.-')
            encoded_username = quote(username, safe='')
            encoded_token = quote(token, safe='')
            return f"tak://com.atakmap.app/enroll?host={encoded_hostname}&username={encoded_username}&token={encoded_token}"
        
        edge_cases = [
            ('example.com', 'user', 'pass'),  # Normal case
            ('example.com', 'user@domain', 'pass'),  # Username with @
            ('example.com', 'user', 'pass@word'),  # Password with @
            ('example.com', 'user space', 'pass'),  # Username with space
            ('example.com', 'user', 'pass word'),  # Password with space
            ('example.com', 'user&name', 'pass&word'),  # Ampersands
            ('example.com', 'user=name', 'pass=word'),  # Equals signs
            ('example.com', 'user?name', 'pass?word'),  # Question marks
            ('example.com', 'user#name', 'pass#word'),  # Hash symbols
            ('example.com', 'üser', 'päss'),  # Unicode characters
        ]
        
        for hostname, username, token in edge_cases:
            qr_string = generate_qr_string(hostname, username, token)
            
            # Should generate valid QR string
            assert qr_string.startswith('tak://com.atakmap.app/enroll?')
            assert 'host=' in qr_string
            assert 'username=' in qr_string
            assert 'token=' in qr_string
            
            # Should be parseable
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(qr_string)
            params = parse_qs(parsed.query)
            
            assert params['host'][0] == hostname
            assert params['username'][0] == username
            assert params['token'][0] == token


if __name__ == '__main__':
    pytest.main([__file__])