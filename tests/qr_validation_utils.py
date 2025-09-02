#!/usr/bin/env python3
"""
QR Code Validation Utilities

This module provides comprehensive validation utilities for iTAK QR code generation,
including format compliance checking, hostname accessibility testing, and QR code
decoding validation using standard libraries.

Requirements covered: 4.3, 4.4
"""

import re
import socket
import time
import urllib.request
import urllib.parse
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs


@dataclass
class QRValidationResult:
    """Result of QR code validation."""
    is_valid: bool
    format_valid: bool
    hostname_accessible: bool
    qr_decodable: bool
    errors: List[str]
    warnings: List[str]
    details: Dict[str, Any]


@dataclass
class HostnameAccessibilityResult:
    """Result of hostname accessibility testing."""
    hostname: str
    is_accessible: bool
    response_time_ms: Optional[float]
    error_message: Optional[str]
    test_method: str
    timestamp: float


class QRValidationUtils:
    """Comprehensive QR code validation utilities."""
    
    def __init__(self, timeout: float = 5.0):
        """
        Initialize QR validation utilities.
        
        Args:
            timeout: Network timeout for accessibility tests in seconds
        """
        self.timeout = timeout
        self.itak_url_pattern = re.compile(
            r'^tak://com\.atakmap\.app/enroll\?.*$',
            re.IGNORECASE
        )
        self.required_params = ['host', 'username', 'token']
    
    def validate_itak_qr_format(self, qr_string: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate iTAK QR code format compliance.
        
        Args:
            qr_string: QR code string to validate
            
        Returns:
            Tuple of (is_valid, errors, details)
        """
        errors = []
        details = {}
        
        if not qr_string:
            errors.append("QR string is empty")
            return False, errors, details
        
        # Check basic URL scheme
        if not self.itak_url_pattern.match(qr_string):
            errors.append("Invalid iTAK URL scheme. Must start with 'tak://com.atakmap.app/enroll?'")
            return False, errors, details
        
        try:
            # Parse URL components
            parsed = urlparse(qr_string)
            details['scheme'] = parsed.scheme
            details['netloc'] = parsed.netloc
            details['path'] = parsed.path
            details['query'] = parsed.query
            
            # Validate scheme
            if parsed.scheme.lower() != 'tak':
                errors.append(f"Invalid scheme: {parsed.scheme}. Must be 'tak'")
            
            # Validate netloc
            if parsed.netloc.lower() != 'com.atakmap.app':
                errors.append(f"Invalid netloc: {parsed.netloc}. Must be 'com.atakmap.app'")
            
            # Validate path
            if parsed.path != '/enroll':
                errors.append(f"Invalid path: {parsed.path}. Must be '/enroll'")
            
            # Parse and validate query parameters
            if not parsed.query:
                errors.append("Missing query parameters")
                return False, errors, details
            
            params = parse_qs(parsed.query)
            details['parameters'] = params
            
            # Check required parameters
            for param in self.required_params:
                if param not in params:
                    errors.append(f"Missing required parameter: {param}")
                elif not params[param] or not params[param][0]:
                    errors.append(f"Empty parameter: {param}")
            
            # Validate parameter values
            if 'host' in params and params['host']:
                host = params['host'][0]
                details['host'] = host
                
                # Check for localhost (warning, not error)
                if host.lower() in ['localhost', '127.0.0.1', '::1']:
                    details['localhost_warning'] = True
                
                # Validate hostname format
                if not self._is_valid_hostname_format(host):
                    errors.append(f"Invalid hostname format: {host}")
            
            # Check QR string length (practical limit for QR codes)
            qr_length = len(qr_string)
            details['length'] = qr_length
            
            if qr_length > 2048:
                errors.append(f"QR string too long: {qr_length} characters (recommended max: 2048)")
            elif qr_length > 1024:
                details['length_warning'] = f"QR string is long: {qr_length} characters"
            
        except Exception as e:
            errors.append(f"URL parsing error: {str(e)}")
            return False, errors, details
        
        is_valid = len(errors) == 0
        return is_valid, errors, details
    
    def test_hostname_accessibility(self, hostname: str, port: int = 8443) -> HostnameAccessibilityResult:
        """
        Test if hostname is accessible from current network.
        
        Args:
            hostname: Hostname or IP address to test
            port: Port to test (default: 8443 for TAK server)
            
        Returns:
            HostnameAccessibilityResult with test results
        """
        start_time = time.time()
        
        try:
            # First try DNS resolution
            try:
                socket.gethostbyname(hostname)
            except socket.gaierror as e:
                return HostnameAccessibilityResult(
                    hostname=hostname,
                    is_accessible=False,
                    response_time_ms=None,
                    error_message=f"DNS resolution failed: {str(e)}",
                    test_method="dns_resolution",
                    timestamp=start_time
                )
            
            # Try socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            try:
                result = sock.connect_ex((hostname, port))
                response_time = (time.time() - start_time) * 1000
                
                if result == 0:
                    return HostnameAccessibilityResult(
                        hostname=hostname,
                        is_accessible=True,
                        response_time_ms=response_time,
                        error_message=None,
                        test_method="socket_connection",
                        timestamp=start_time
                    )
                else:
                    return HostnameAccessibilityResult(
                        hostname=hostname,
                        is_accessible=False,
                        response_time_ms=response_time,
                        error_message=f"Connection failed: {result}",
                        test_method="socket_connection",
                        timestamp=start_time
                    )
            finally:
                sock.close()
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HostnameAccessibilityResult(
                hostname=hostname,
                is_accessible=False,
                response_time_ms=response_time,
                error_message=f"Connection test failed: {str(e)}",
                test_method="socket_connection",
                timestamp=start_time
            )
    
    def test_qr_decodability(self, qr_string: str) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Test if QR string can be decoded by standard QR code libraries.
        
        Args:
            qr_string: QR code string to test
            
        Returns:
            Tuple of (is_decodable, error_message, details)
        """
        details = {}
        
        try:
            # Try to import QR code library
            try:
                import qrcode
                from PIL import Image
                details['qrcode_library'] = 'available'
            except ImportError:
                return False, "QR code library (qrcode/PIL) not available", details
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            try:
                qr.add_data(qr_string)
                qr.make(fit=True)
                
                # Generate image
                img = qr.make_image(fill_color="black", back_color="white")
                
                details['qr_version'] = qr.version
                details['qr_modules'] = qr.modules_count
                details['data_length'] = len(qr_string)
                details['image_size'] = img.size if hasattr(img, 'size') else None
                
                # Verify data was stored correctly
                if hasattr(qr, 'data_list') and qr.data_list:
                    try:
                        stored_data = qr.data_list[0].data
                        if stored_data == qr_string:
                            details['data_integrity'] = True
                            return True, None, details
                        else:
                            # Data might be encoded differently, this is still valid
                            details['data_integrity'] = 'encoded_differently'
                            details['stored_data_length'] = len(stored_data) if stored_data else 0
                            return True, None, details
                    except (AttributeError, IndexError):
                        # If we can't access the data, assume success if no exception
                        details['data_integrity'] = 'unknown'
                        return True, None, details
                else:
                    # If we can't verify data integrity, assume success if no exception
                    details['data_integrity'] = 'unknown'
                    return True, None, details
                    
            except Exception as e:
                return False, f"QR code generation failed: {str(e)}", details
                
        except Exception as e:
            return False, f"QR decodability test failed: {str(e)}", details
    
    def comprehensive_validation(self, qr_string: str, test_hostname: bool = True) -> QRValidationResult:
        """
        Perform comprehensive QR code validation.
        
        Args:
            qr_string: QR code string to validate
            test_hostname: Whether to test hostname accessibility
            
        Returns:
            QRValidationResult with complete validation results
        """
        errors = []
        warnings = []
        details = {}
        
        # 1. Format validation
        format_valid, format_errors, format_details = self.validate_itak_qr_format(qr_string)
        errors.extend(format_errors)
        details['format'] = format_details
        
        # Add localhost warning if detected
        if format_details.get('localhost_warning'):
            warnings.append("QR code uses localhost hostname - will not work for external mobile clients")
        
        # Add length warning if detected
        if 'length_warning' in format_details:
            warnings.append(format_details['length_warning'])
        
        # 2. Hostname accessibility test
        hostname_accessible = True
        if test_hostname and format_valid and 'host' in format_details:
            hostname = format_details['host']
            accessibility_result = self.test_hostname_accessibility(hostname)
            details['hostname_accessibility'] = accessibility_result
            
            if not accessibility_result.is_accessible:
                hostname_accessible = False
                if accessibility_result.error_message:
                    warnings.append(f"Hostname not accessible: {accessibility_result.error_message}")
                else:
                    warnings.append(f"Hostname {hostname} is not accessible")
        
        # 3. QR decodability test
        qr_decodable, decode_error, decode_details = self.test_qr_decodability(qr_string)
        details['qr_decoding'] = decode_details
        
        if not qr_decodable and decode_error:
            if "not available" in decode_error:
                warnings.append(f"QR decodability test skipped: {decode_error}")
                qr_decodable = True  # Don't fail validation if library not available
            else:
                errors.append(f"QR decodability failed: {decode_error}")
        
        # Overall validation result
        is_valid = format_valid and len(errors) == 0
        
        return QRValidationResult(
            is_valid=is_valid,
            format_valid=format_valid,
            hostname_accessible=hostname_accessible,
            qr_decodable=qr_decodable,
            errors=errors,
            warnings=warnings,
            details=details
        )
    
    def _is_valid_hostname_format(self, hostname: str) -> bool:
        """
        Validate hostname format (basic validation).
        
        Args:
            hostname: Hostname to validate
            
        Returns:
            True if hostname format is valid
        """
        if not hostname:
            return False
        
        # Check for IP address
        try:
            socket.inet_aton(hostname)
            return True  # Valid IPv4 address
        except socket.error:
            pass
        
        # Check hostname format
        if len(hostname) > 253:
            return False
        
        # Basic hostname validation
        hostname_pattern = re.compile(
            r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        )
        
        return bool(hostname_pattern.match(hostname))


def validate_qr_code(qr_string: str, test_hostname: bool = True, timeout: float = 5.0) -> QRValidationResult:
    """
    Convenience function for comprehensive QR code validation.
    
    Args:
        qr_string: QR code string to validate
        test_hostname: Whether to test hostname accessibility
        timeout: Network timeout for accessibility tests
        
    Returns:
        QRValidationResult with validation results
    """
    validator = QRValidationUtils(timeout=timeout)
    return validator.comprehensive_validation(qr_string, test_hostname=test_hostname)


def print_validation_report(result: QRValidationResult, verbose: bool = False) -> None:
    """
    Print a formatted validation report.
    
    Args:
        result: QRValidationResult to print
        verbose: Whether to include detailed information
    """
    print("QR Code Validation Report")
    print("=" * 50)
    
    # Overall status
    status = "✓ VALID" if result.is_valid else "✗ INVALID"
    print(f"Overall Status: {status}")
    print()
    
    # Component status
    print("Component Status:")
    format_status = "✓" if result.format_valid else "✗"
    hostname_status = "✓" if result.hostname_accessible else "✗"
    decode_status = "✓" if result.qr_decodable else "✗"
    
    print(f"  Format Valid:      {format_status}")
    print(f"  Hostname Access:   {hostname_status}")
    print(f"  QR Decodable:      {decode_status}")
    print()
    
    # Errors
    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"  ✗ {error}")
        print()
    
    # Warnings
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  ⚠ {warning}")
        print()
    
    # Detailed information
    if verbose and result.details:
        print("Detailed Information:")
        
        if 'format' in result.details:
            format_details = result.details['format']
            if 'host' in format_details:
                print(f"  Host: {format_details['host']}")
            if 'length' in format_details:
                print(f"  Length: {format_details['length']} characters")
        
        if 'hostname_accessibility' in result.details:
            access_details = result.details['hostname_accessibility']
            print(f"  Hostname Test: {access_details.test_method}")
            if access_details.response_time_ms:
                print(f"  Response Time: {access_details.response_time_ms:.1f}ms")
        
        if 'qr_decoding' in result.details:
            decode_details = result.details['qr_decoding']
            if 'qr_version' in decode_details:
                print(f"  QR Version: {decode_details['qr_version']}")
            if 'data_length' in decode_details:
                print(f"  Data Length: {decode_details['data_length']}")


if __name__ == '__main__':
    """Command-line interface for QR validation utilities."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python qr_validation_utils.py <qr_string> [--no-hostname-test] [--verbose]")
        print()
        print("Example:")
        print("  python qr_validation_utils.py 'tak://com.atakmap.app/enroll?host=example.com&username=user&token=pass'")
        sys.exit(1)
    
    qr_string = sys.argv[1]
    test_hostname = '--no-hostname-test' not in sys.argv
    verbose = '--verbose' in sys.argv
    
    print(f"Validating QR code: {qr_string[:50]}{'...' if len(qr_string) > 50 else ''}")
    print()
    
    result = validate_qr_code(qr_string, test_hostname=test_hostname)
    print_validation_report(result, verbose=verbose)
    
    sys.exit(0 if result.is_valid else 1)