#!/usr/bin/env python3
"""
Demonstration script for QR validation utilities.
Shows all the validation features working without external dependencies.
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tests.qr_validation_utils import QRValidationUtils, validate_qr_code, print_validation_report


def demo_qr_validation():
    """Demonstrate QR validation utilities."""
    print("QR Code Validation Utilities Demo")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Valid QR with External IP",
            "qr": "tak://com.atakmap.app/enroll?host=192.168.1.100&username=testuser&token=testpass",
            "expected": "valid"
        },
        {
            "name": "Valid QR with Localhost (Warning Expected)",
            "qr": "tak://com.atakmap.app/enroll?host=localhost&username=testuser&token=testpass",
            "expected": "valid_with_warning"
        },
        {
            "name": "Invalid QR - Wrong Scheme",
            "qr": "http://com.atakmap.app/enroll?host=example.com&username=user&token=pass",
            "expected": "invalid"
        },
        {
            "name": "Invalid QR - Missing Parameter",
            "qr": "tak://com.atakmap.app/enroll?host=example.com&username=user",
            "expected": "invalid"
        },
        {
            "name": "Valid QR with Special Characters",
            "qr": "tak://com.atakmap.app/enroll?host=example.com&username=user@domain.com&token=pass!@#$",
            "expected": "valid"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {case['name']}")
        print("-" * 40)
        
        # Validate QR code (skip hostname test to avoid network dependencies)
        result = validate_qr_code(case['qr'], test_hostname=False)
        
        # Check results
        success = False
        
        if case['expected'] == 'valid':
            success = result.is_valid and len(result.errors) == 0
        elif case['expected'] == 'valid_with_warning':
            success = result.is_valid and len(result.warnings) > 0
        elif case['expected'] == 'invalid':
            success = not result.is_valid and len(result.errors) > 0
        
        if success:
            print(f"✓ Test PASSED")
            passed += 1
        else:
            print(f"✗ Test FAILED")
            print(f"  Expected: {case['expected']}")
            print(f"  Got: valid={result.is_valid}, errors={len(result.errors)}, warnings={len(result.warnings)}")
            failed += 1
        
        # Show brief results
        print(f"  Format Valid: {'✓' if result.format_valid else '✗'}")
        print(f"  QR Decodable: {'✓' if result.qr_decodable else '✗'}")
        
        if result.errors:
            print(f"  Errors: {len(result.errors)}")
            for error in result.errors[:2]:  # Show first 2 errors
                print(f"    - {error}")
        
        if result.warnings:
            print(f"  Warnings: {len(result.warnings)}")
            for warning in result.warnings[:2]:  # Show first 2 warnings
                print(f"    - {warning}")
    
    print(f"\n{'='*50}")
    print(f"Demo Results: {passed} passed, {failed} failed")
    
    return failed == 0


def demo_hostname_accessibility():
    """Demonstrate hostname accessibility testing."""
    print("\n\nHostname Accessibility Testing Demo")
    print("=" * 50)
    
    validator = QRValidationUtils(timeout=2.0)
    
    test_hosts = [
        ("localhost", "Should be accessible"),
        ("invalid.nonexistent.domain.test", "Should fail with DNS error"),
        ("127.0.0.1", "Should be accessible (loopback)")
    ]
    
    for hostname, description in test_hosts:
        print(f"\nTesting: {hostname}")
        print(f"Expected: {description}")
        
        result = validator.test_hostname_accessibility(hostname, port=22)  # SSH port
        
        print(f"Result: {'✓ Accessible' if result.is_accessible else '✗ Not accessible'}")
        if result.response_time_ms:
            print(f"Response time: {result.response_time_ms:.1f}ms")
        if result.error_message:
            print(f"Error: {result.error_message}")


def demo_qr_format_validation():
    """Demonstrate QR format validation."""
    print("\n\nQR Format Validation Demo")
    print("=" * 50)
    
    validator = QRValidationUtils()
    
    format_tests = [
        ("Valid format", "tak://com.atakmap.app/enroll?host=example.com&username=user&token=pass"),
        ("Wrong scheme", "http://com.atakmap.app/enroll?host=example.com&username=user&token=pass"),
        ("Wrong domain", "tak://wrong.domain.com/enroll?host=example.com&username=user&token=pass"),
        ("Missing parameters", "tak://com.atakmap.app/enroll?host=example.com"),
        ("Empty parameters", "tak://com.atakmap.app/enroll?host=&username=&token="),
    ]
    
    for test_name, qr_string in format_tests:
        print(f"\n{test_name}:")
        is_valid, errors, details = validator.validate_itak_qr_format(qr_string)
        
        print(f"  Valid: {'✓' if is_valid else '✗'}")
        if errors:
            print(f"  Errors: {len(errors)}")
            for error in errors[:2]:
                print(f"    - {error}")
        
        if 'length' in details:
            print(f"  Length: {details['length']} characters")


def main():
    """Run all demos."""
    print("iTAK QR Code Validation Utilities")
    print("Complete Feature Demonstration")
    print("=" * 60)
    
    success = True
    
    try:
        # Demo 1: QR Validation
        if not demo_qr_validation():
            success = False
        
        # Demo 2: Hostname Accessibility
        demo_hostname_accessibility()
        
        # Demo 3: Format Validation
        demo_qr_format_validation()
        
        print(f"\n{'='*60}")
        if success:
            print("🎉 All validation utilities are working correctly!")
            print("\nFeatures demonstrated:")
            print("✓ iTAK QR code format validation")
            print("✓ Hostname accessibility testing")
            print("✓ QR code decodability testing")
            print("✓ Comprehensive validation with warnings")
            print("✓ Special character handling")
            print("✓ Error detection and reporting")
        else:
            print("❌ Some validation tests failed!")
        
        print(f"\nValidation utilities are ready for use!")
        print("Use: python OpenTAKServer/tests/qr_validation_utils.py <qr_string> --verbose")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        success = False
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)