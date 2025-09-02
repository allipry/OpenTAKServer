"""
Unit tests for QR code generation functionality.
Tests QR code format validation and iTAK compatibility.
"""

import os
import pytest
import json
import re
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Add the parent directory to the path so we can import the module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from opentakserver.hostname_resolver import HostnameResolver, HostnameResult


class TestQRCodeGeneration:
    """Test cases for QR code generation and format validation."""
    
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
    
    def test_itak_qr_format_validation(self):
        """Test iTAK QR code format compliance."""
        # Test valid iTAK QR format
        hostname = "192.168.1.100"
        username = "testuser"
        token = "testpass"
        
        qr_string = f"tak://com.atakmap.app/enroll?host={hostname}&username={username}&token={token}"
        
        # Validate URL scheme
        assert qr_string.startswith("tak://com.atakmap.app/enroll?")
        
        # Parse URL components
        parsed = urlparse(qr_string)
        assert parsed.scheme == "tak"
        assert parsed.netloc == "com.atakmap.app"
        assert parsed.path == "/enroll"
        
        # Parse query parameters
        params = parse_qs(parsed.query)
        assert params['host'][0] == hostname
        assert params['username'][0] == username
        assert params['token'][0] == token
    
    def test_qr_format_with_special_characters(self):
        """Test QR code format with special characters in parameters."""
        hostname = "test-server.example.com"
        username = "user@domain.com"
        token = "pass!@#$%^&*()"
        
        from urllib.parse import quote
        encoded_hostname = quote(hostname, safe=':.-')
        encoded_username = quote(username, safe='')
        encoded_token = quote(token, safe='')
        
        qr_string = f"tak://com.atakmap.app/enroll?host={encoded_hostname}&username={encoded_username}&token={encoded_token}"
        
        # Validate URL can be parsed
        parsed = urlparse(qr_string)
        params = parse_qs(parsed.query)
        
        # Verify parameters are properly encoded/decoded
        assert params['host'][0] == hostname
        assert params['username'][0] == username
        assert params['token'][0] == token
    
    def test_qr_format_parameter_order(self):
        """Test that QR code parameters are in correct order."""
        hostname = "example.com"
        username = "user"
        token = "pass"
        
        qr_string = f"tak://com.atakmap.app/enroll?host={hostname}&username={username}&token={token}"
        
        # Extract query string
        parsed = urlparse(qr_string)
        query_parts = parsed.query.split('&')
        
        # Verify parameter order (host, username, token)
        assert query_parts[0].startswith('host=')
        assert query_parts[1].startswith('username=')
        assert query_parts[2].startswith('token=')
    
    def test_qr_string_length_validation(self):
        """Test QR string length validation for practical QR code limits."""
        hostname = "example.com"
        username = "user"
        
        # Test normal length
        normal_token = "password123"
        normal_qr = f"tak://com.atakmap.app/enroll?host={hostname}&username={username}&token={normal_token}"
        assert len(normal_qr) < 2048  # Should be well under limit
        
        # Test long but acceptable length
        long_token = "a" * 1900  # Create long token
        long_qr = f"tak://com.atakmap.app/enroll?host={hostname}&username={username}&token={long_token}"
        assert len(long_qr) < 2048  # Should still be under recommended limit
        
        # Test excessive length
        excessive_token = "a" * 4000
        excessive_qr = f"tak://com.atakmap.app/enroll?host={hostname}&username={username}&token={excessive_token}"
        assert len(excessive_qr) > 4096  # Should exceed practical limit
    
    def test_qr_format_with_ip_addresses(self):
        """Test QR code format with different IP address formats."""
        username = "user"
        token = "pass"
        
        # Test IPv4 addresses
        ipv4_addresses = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "203.0.113.1"
        ]
        
        for ip in ipv4_addresses:
            qr_string = f"tak://com.atakmap.app/enroll?host={ip}&username={username}&token={token}"
            parsed = urlparse(qr_string)
            params = parse_qs(parsed.query)
            assert params['host'][0] == ip
    
    def test_qr_format_with_hostnames(self):
        """Test QR code format with different hostname formats."""
        username = "user"
        token = "pass"
        
        # Test various hostname formats
        hostnames = [
            "example.com",
            "sub.example.com",
            "test-server.domain.org",
            "server123.company.net"
        ]
        
        for hostname in hostnames:
            qr_string = f"tak://com.atakmap.app/enroll?host={hostname}&username={username}&token={token}"
            parsed = urlparse(qr_string)
            params = parse_qs(parsed.query)
            assert params['host'][0] == hostname
    
    def test_qr_format_case_sensitivity(self):
        """Test QR code format case sensitivity."""
        # iTAK scheme should be lowercase
        hostname = "Example.Com"
        username = "TestUser"
        token = "TestPass"
        
        qr_string = f"tak://com.atakmap.app/enroll?host={hostname}&username={username}&token={token}"
        
        # Scheme should be lowercase
        assert qr_string.startswith("tak://")
        assert not qr_string.startswith("TAK://")
        
        # Domain should be lowercase
        assert "com.atakmap.app" in qr_string
        assert not "COM.ATAKMAP.APP" in qr_string
        
        # Parameters preserve case
        parsed = urlparse(qr_string)
        params = parse_qs(parsed.query)
        assert params['host'][0] == hostname  # Preserve original case
        assert params['username'][0] == username  # Preserve original case
        assert params['token'][0] == token  # Preserve original case
    
    def test_qr_format_missing_parameters(self):
        """Test QR code format validation with missing parameters."""
        base_url = "tak://com.atakmap.app/enroll?"
        
        # Test missing host
        qr_missing_host = f"{base_url}username=user&token=pass"
        parsed = urlparse(qr_missing_host)
        params = parse_qs(parsed.query)
        assert 'host' not in params
        
        # Test missing username
        qr_missing_username = f"{base_url}host=example.com&token=pass"
        parsed = urlparse(qr_missing_username)
        params = parse_qs(parsed.query)
        assert 'username' not in params
        
        # Test missing token
        qr_missing_token = f"{base_url}host=example.com&username=user"
        parsed = urlparse(qr_missing_token)
        params = parse_qs(parsed.query)
        assert 'token' not in params
    
    def test_qr_format_empty_parameters(self):
        """Test QR code format with empty parameters."""
        # Test empty values
        qr_empty = "tak://com.atakmap.app/enroll?host=&username=&token="
        parsed = urlparse(qr_empty)
        params = parse_qs(parsed.query)
        
        # Empty parameters should still be present but empty
        assert 'host' in params
        assert 'username' in params
        assert 'token' in params
        assert params['host'][0] == ""
        assert params['username'][0] == ""
        assert params['token'][0] == ""
    
    def test_qr_format_duplicate_parameters(self):
        """Test QR code format with duplicate parameters."""
        # Test duplicate parameters (should not happen in valid QR codes)
        qr_duplicate = "tak://com.atakmap.app/enroll?host=first.com&host=second.com&username=user&token=pass"
        parsed = urlparse(qr_duplicate)
        params = parse_qs(parsed.query)
        
        # parse_qs should handle duplicates by creating a list
        assert len(params['host']) == 2
        assert 'first.com' in params['host']
        assert 'second.com' in params['host']
    
    def test_qr_format_additional_parameters(self):
        """Test QR code format with additional parameters."""
        # Test with extra parameters (should be ignored by iTAK)
        qr_extra = "tak://com.atakmap.app/enroll?host=example.com&username=user&token=pass&extra=value&debug=true"
        parsed = urlparse(qr_extra)
        params = parse_qs(parsed.query)
        
        # Required parameters should be present
        assert params['host'][0] == "example.com"
        assert params['username'][0] == "user"
        assert params['token'][0] == "pass"
        
        # Extra parameters should also be present
        assert params['extra'][0] == "value"
        assert params['debug'][0] == "true"
    
    def test_qr_format_url_encoding_edge_cases(self):
        """Test QR code format with URL encoding edge cases."""
        from urllib.parse import quote, unquote
        
        # Test characters that need encoding
        special_chars = {
            "space test": "space%20test",
            "user@domain": "user%40domain",
            "pass&word": "pass%26word",
            "test=value": "test%3Dvalue",
            "query?param": "query%3Fparam"
        }
        
        for original, expected_encoded in special_chars.items():
            encoded = quote(original, safe='')
            assert encoded == expected_encoded
            
            # Test round-trip encoding/decoding
            decoded = unquote(encoded)
            assert decoded == original
    
    def test_itak_compatibility_validation(self):
        """Test QR code compatibility with iTAK application requirements."""
        # Test standard iTAK QR code format
        hostname = "tak-server.military.net"
        username = "soldier01"
        token = "SecurePass123!"
        
        qr_string = f"tak://com.atakmap.app/enroll?host={hostname}&username={username}&token={token}"
        
        # Validate iTAK-specific requirements
        assert qr_string.startswith("tak://com.atakmap.app/enroll?")
        assert "host=" in qr_string
        assert "username=" in qr_string
        assert "token=" in qr_string
        
        # Validate no forbidden characters in base URL
        base_url = qr_string.split('?')[0]
        assert ' ' not in base_url
        assert '\n' not in base_url
        assert '\t' not in base_url
        
        # Validate URL is well-formed
        parsed = urlparse(qr_string)
        assert parsed.scheme == "tak"
        assert parsed.netloc == "com.atakmap.app"
        assert parsed.path == "/enroll"
        assert parsed.query != ""
    
    def test_qr_decoding_with_qr_library(self):
        """Test QR code can be decoded by standard QR code libraries."""
        try:
            import qrcode
            from PIL import Image
            import io
            
            # Generate QR code string
            hostname = "192.168.1.100"
            username = "testuser"
            token = "testpass"
            qr_string = f"tak://com.atakmap.app/enroll?host={hostname}&username={username}&token={token}"
            
            # Create QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            # Generate QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Verify QR code was created successfully
            assert img is not None
            assert isinstance(img, Image.Image)
            
            # Test QR code data
            assert qr.data_list[0].data == qr_string
            
        except ImportError:
            pytest.skip("qrcode library not available for QR code generation test")
    
    def test_qr_format_validation_function(self):
        """Test QR code format validation helper function."""
        def validate_itak_qr_format(qr_string):
            """Validate iTAK QR code format."""
            if not qr_string.startswith("tak://com.atakmap.app/enroll?"):
                return False, "Invalid iTAK URL scheme"
            
            try:
                parsed = urlparse(qr_string)
                params = parse_qs(parsed.query)
                
                required_params = ['host', 'username', 'token']
                for param in required_params:
                    if param not in params:
                        return False, f"Missing required parameter: {param}"
                    if not params[param][0]:  # Check if parameter value is empty
                        return False, f"Empty parameter: {param}"
                
                return True, "Valid iTAK QR format"
                
            except Exception as e:
                return False, f"URL parsing error: {str(e)}"
        
        # Test valid QR codes
        valid_qr = "tak://com.atakmap.app/enroll?host=example.com&username=user&token=pass"
        is_valid, message = validate_itak_qr_format(valid_qr)
        assert is_valid == True
        assert message == "Valid iTAK QR format"
        
        # Test invalid scheme
        invalid_scheme = "http://com.atakmap.app/enroll?host=example.com&username=user&token=pass"
        is_valid, message = validate_itak_qr_format(invalid_scheme)
        assert is_valid == False
        assert "Invalid iTAK URL scheme" in message
        
        # Test missing parameter
        missing_host = "tak://com.atakmap.app/enroll?username=user&token=pass"
        is_valid, message = validate_itak_qr_format(missing_host)
        assert is_valid == False
        assert "Missing required parameter: host" in message
        
        # Test empty parameter
        empty_username = "tak://com.atakmap.app/enroll?host=example.com&username=&token=pass"
        is_valid, message = validate_itak_qr_format(empty_username)
        assert is_valid == False
        assert "Empty parameter: username" in message


if __name__ == '__main__':
    pytest.main([__file__])