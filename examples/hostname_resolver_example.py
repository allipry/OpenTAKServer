#!/usr/bin/env python3
"""
Example usage of the HostnameResolver service.

This script demonstrates how to use the hostname resolution service
for iTAK QR code generation.
"""

import os
import sys

# Add the parent directory to the path so we can import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from opentakserver.hostname_resolver import HostnameResolver


def main():
    """Demonstrate hostname resolution functionality."""
    print("=== Hostname Resolution Service Example ===\n")
    
    resolver = HostnameResolver()
    
    # Example 1: Basic usage with override
    print("1. Using hostname override:")
    result = resolver.get_external_hostname(override_host='myserver.example.com')
    print(f"   Hostname: {result.hostname}")
    print(f"   Method: {result.detection_method}")
    print(f"   External accessible: {result.is_external_accessible}")
    print(f"   Warnings: {result.warnings}")
    print()
    
    # Example 2: Environment variable configuration
    print("2. Using environment variable:")
    os.environ['EXTERNAL_HOST'] = 'env-server.example.com'
    resolver_env = HostnameResolver()
    result = resolver_env.get_external_hostname()
    print(f"   Hostname: {result.hostname}")
    print(f"   Method: {result.detection_method}")
    print(f"   External accessible: {result.is_external_accessible}")
    del os.environ['EXTERNAL_HOST']
    print()
    
    # Example 3: Request host handling
    print("3. Using request host (non-localhost):")
    result = resolver.get_external_hostname(request_host='api.example.com:8443')
    print(f"   Hostname: {result.hostname}")
    print(f"   Method: {result.detection_method}")
    print(f"   External accessible: {result.is_external_accessible}")
    print()
    
    # Example 4: Localhost detection and warnings
    print("4. Localhost detection (with warnings):")
    result = resolver.get_external_hostname(request_host='localhost:8080')
    print(f"   Hostname: {result.hostname}")
    print(f"   Method: {result.detection_method}")
    print(f"   Is localhost: {result.is_localhost}")
    print(f"   External accessible: {result.is_external_accessible}")
    print(f"   Warnings: {result.warnings}")
    print()
    
    # Example 5: Hostname validation
    print("5. Hostname validation examples:")
    test_hostnames = [
        'valid.example.com',
        '192.168.1.100',
        'localhost',
        'invalid..hostname',
        '256.1.1.1',
        ''
    ]
    
    for hostname in test_hostnames:
        is_valid, msg = resolver.validate_hostname(hostname)
        is_localhost = resolver.is_localhost_address(hostname)
        print(f"   '{hostname}': valid={is_valid}, localhost={is_localhost}")
        if not is_valid:
            print(f"      Error: {msg}")
    print()
    
    # Example 6: External IP detection (if available)
    print("6. External IP detection:")
    try:
        external_ip = resolver.get_external_ip()
        if external_ip:
            print(f"   Detected external IP: {external_ip}")
        else:
            print("   External IP detection failed")
    except Exception as e:
        print(f"   External IP detection error: {e}")
    print()
    
    print("=== Example Complete ===")


if __name__ == '__main__':
    main()