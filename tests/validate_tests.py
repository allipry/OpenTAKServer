#!/usr/bin/env python3
"""
Simple test validation script to verify test functionality without external dependencies.
"""

import sys
import os
from urllib.parse import urlparse, parse_qs

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from opentakserver.hostname_resolver import HostnameResolver, HostnameResult
    print("✓ Successfully imported HostnameResolver")
except ImportError as e:
    print(f"✗ Failed to import HostnameResolver: {e}")
    sys.exit(1)

try:
    from tests.qr_validation_utils import QRValidationUtils, validate_qr_code
    print("✓ Successfully imported QR validation utilities")
except ImportError as e:
    print(f"✗ Failed to import QR validation utilities: {e}")
    sys.exit(1)


def test_hostname_resolver_basic():
    """Test basic hostname resolver functionality."""
    print("\n--- Testing Hostname Resolver ---")
    
    resolver = HostnameResolver()
    
    # Test localhost detection
    test_cases = [
        ('localhost', True),
        ('127.0.0.1', True),
        ('example.com', False),
        ('192.168.1.1', False),
    ]
    
    for hostname, expected in test_cases:
        result = resolver.is_localhost_address(hostname)
        if result == expected:
            print(f"✓ Localhost detection for '{hostname}': {result}")
        else:
            print(f"✗ Localhost detection for '{hostname}': expected {expected}, got {result}")
            return False
    
    # Test hostname validation
    validation_cases = [
        ('example.com', True),
        ('192.168.1.1', True),
        ('', False),
        ('invalid..hostname', False),
    ]
    
    for hostname, expected in validation_cases:
        is_valid, msg = resolver.validate_hostname(hostname)
        if is_valid == expected:
            print(f"✓ Hostname validation for '{hostname}': {is_valid}")
        else:
            print(f"✗ Hostname validation for '{hostname}': expected {expected}, got {is_valid} ({msg})")
            return False
    
    return True


def test_qr_code_format():
    """Test QR code format validation."""
    print("\n--- Testing QR Code Format ---")
    
    # Test valid iTAK QR format
    hostname = "192.168.1.100"
    username = "testuser"
    token = "testpass"
    
    qr_string = f"tak://com.atakmap.app/enroll?host={hostname}&username={username}&token={token}"
    
    # Validate URL scheme
    if not qr_string.startswith("tak://com.atakmap.app/enroll?"):
        print(f"✗ Invalid QR string format: {qr_string}")
        return False
    
    print(f"✓ QR string format is valid")
    
    # Parse URL components
    try:
        parsed = urlparse(qr_string)
        if parsed.scheme != "tak":
            print(f"✗ Invalid scheme: {parsed.scheme}")
            return False
        
        if parsed.netloc != "com.atakmap.app":
            print(f"✗ Invalid netloc: {parsed.netloc}")
            return False
        
        if parsed.path != "/enroll":
            print(f"✗ Invalid path: {parsed.path}")
            return False
        
        print(f"✓ URL components are valid")
        
        # Parse query parameters
        params = parse_qs(parsed.query)
        if params['host'][0] != hostname:
            print(f"✗ Invalid host parameter: {params['host'][0]}")
            return False
        
        if params['username'][0] != username:
            print(f"✗ Invalid username parameter: {params['username'][0]}")
            return False
        
        if params['token'][0] != token:
            print(f"✗ Invalid token parameter: {params['token'][0]}")
            return False
        
        print(f"✓ Query parameters are valid")
        
    except Exception as e:
        print(f"✗ Error parsing QR string: {e}")
        return False
    
    return True


def test_special_characters():
    """Test QR code format with special characters."""
    print("\n--- Testing Special Characters ---")
    
    from urllib.parse import quote, unquote
    
    test_cases = [
        ("user@domain.com", "user%40domain.com"),
        ("pass word", "pass%20word"),
        ("user&name", "user%26name"),
        ("test=value", "test%3Dvalue"),
    ]
    
    for original, expected_encoded in test_cases:
        encoded = quote(original, safe='')
        if encoded == expected_encoded:
            print(f"✓ URL encoding for '{original}': {encoded}")
        else:
            print(f"✗ URL encoding for '{original}': expected {expected_encoded}, got {encoded}")
            return False
        
        # Test round-trip
        decoded = unquote(encoded)
        if decoded == original:
            print(f"✓ URL decoding for '{encoded}': {decoded}")
        else:
            print(f"✗ URL decoding for '{encoded}': expected {original}, got {decoded}")
            return False
    
    return True


def test_deployment_scenarios():
    """Test different deployment scenarios."""
    print("\n--- Testing Deployment Scenarios ---")
    
    resolver = HostnameResolver()
    
    # Test localhost scenario
    with patch_disable_external_ip(resolver):
        result = resolver.get_external_hostname(request_host='localhost:8080')
        if result.hostname == 'localhost' and result.is_localhost:
            print("✓ Localhost scenario handled correctly")
        else:
            print(f"✗ Localhost scenario failed: {result.hostname}, is_localhost: {result.is_localhost}")
            return False
    
    # Test external hostname scenario
    with patch_disable_external_ip(resolver):
        result = resolver.get_external_hostname(request_host='example.com:8080')
        if result.hostname == 'example.com' and not result.is_localhost:
            print("✓ External hostname scenario handled correctly")
        else:
            print(f"✗ External hostname scenario failed: {result.hostname}, is_localhost: {result.is_localhost}")
            return False
    
    # Test override scenario
    result = resolver.get_external_hostname(
        request_host='localhost:8080',
        override_host='override.example.com'
    )
    if result.hostname == 'override.example.com' and result.detection_method == 'override':
        print("✓ Override scenario handled correctly")
    else:
        print(f"✗ Override scenario failed: {result.hostname}, method: {result.detection_method}")
        return False
    
    return True


def patch_disable_external_ip(resolver):
    """Simple context manager to disable external IP detection."""
    class DisableExternalIP:
        def __enter__(self):
            resolver._disable_external_ip = True
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            resolver._disable_external_ip = False
    
    return DisableExternalIP()


def test_error_handling():
    """Test error handling scenarios."""
    print("\n--- Testing Error Handling ---")
    
    resolver = HostnameResolver()
    
    # Test None inputs
    result = resolver.get_external_hostname(request_host=None, override_host=None)
    if result.hostname is not None:
        print("✓ None input handling works")
    else:
        print("✗ None input handling failed")
        return False
    
    # Test empty string inputs
    with patch_disable_external_ip(resolver):
        result = resolver.get_external_hostname(request_host='', override_host=None)
        if result.hostname is not None:
            print("✓ Empty string input handling works")
        else:
            print("✗ Empty string input handling failed")
            return False
    
    # Test invalid hostname validation
    is_valid, msg = resolver.validate_hostname('invalid..hostname')
    if not is_valid and msg:
        print("✓ Invalid hostname validation works")
    else:
        print("✗ Invalid hostname validation failed")
        return False
    
    return True


def test_qr_validation_utilities():
    """Test QR validation utilities functionality."""
    print("\n--- Testing QR Validation Utilities ---")
    
    validator = QRValidationUtils(timeout=2.0)
    
    # Test valid QR code
    valid_qr = "tak://com.atakmap.app/enroll?host=192.168.1.100&username=testuser&token=testpass"
    is_valid, errors, details = validator.validate_itak_qr_format(valid_qr)
    
    if is_valid and len(errors) == 0:
        print("✓ Valid QR code validation works")
    else:
        print(f"✗ Valid QR code validation failed: {errors}")
        return False
    
    # Test invalid QR code
    invalid_qr = "http://wrong.scheme/enroll?host=example.com&username=user&token=pass"
    is_valid, errors, details = validator.validate_itak_qr_format(invalid_qr)
    
    if not is_valid and len(errors) > 0:
        print("✓ Invalid QR code detection works")
    else:
        print(f"✗ Invalid QR code detection failed: should have errors but got {errors}")
        return False
    
    # Test comprehensive validation (without hostname test to avoid network dependency)
    result = validate_qr_code(valid_qr, test_hostname=False)
    
    if result.format_valid:
        print("✓ Comprehensive QR validation works")
    else:
        print(f"✗ Comprehensive QR validation failed: {result.errors}")
        return False
    
    # Test localhost warning detection
    localhost_qr = "tak://com.atakmap.app/enroll?host=localhost&username=user&token=pass"
    result = validate_qr_code(localhost_qr, test_hostname=False)
    
    if result.format_valid and len(result.warnings) > 0:
        print("✓ Localhost warning detection works")
    else:
        print(f"✗ Localhost warning detection failed: warnings={result.warnings}")
        return False
    
    return True


def test_hostname_accessibility_utils():
    """Test hostname accessibility testing utilities."""
    print("\n--- Testing Hostname Accessibility Utils ---")
    
    validator = QRValidationUtils(timeout=1.0)  # Short timeout for testing
    
    # Test localhost accessibility (should work)
    result = validator.test_hostname_accessibility("localhost", port=22)  # SSH port likely to be available
    
    if result.hostname == "localhost":
        print("✓ Hostname accessibility test structure works")
    else:
        print(f"✗ Hostname accessibility test failed: {result}")
        return False
    
    # Test invalid hostname (should fail)
    result = validator.test_hostname_accessibility("invalid.nonexistent.domain.test", port=8443)
    
    if not result.is_accessible and result.error_message:
        print("✓ Invalid hostname detection works")
    else:
        print(f"✗ Invalid hostname detection failed: {result}")
        return False
    
    return True


def main():
    """Run all validation tests."""
    print("iTAK QR Code Test Validation")
    print("============================")
    
    tests = [
        test_hostname_resolver_basic,
        test_qr_code_format,
        test_special_characters,
        test_deployment_scenarios,
        test_error_handling,
        test_qr_validation_utilities,
        test_hostname_accessibility_utils,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✓ {test.__name__} PASSED")
            else:
                failed += 1
                print(f"✗ {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test.__name__} ERROR: {e}")
    
    print(f"\n--- Test Summary ---")
    print(f"Tests passed: {passed}")
    print(f"Tests failed: {failed}")
    print(f"Total tests: {passed + failed}")
    
    if failed == 0:
        print("🎉 All validation tests passed!")
        return True
    else:
        print("❌ Some validation tests failed!")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)