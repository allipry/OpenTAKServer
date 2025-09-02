"""
Hostname Resolution Service for iTAK QR Code Generation

This module provides intelligent hostname detection and validation for generating
QR codes that work with external iTAK mobile clients. It handles environment
variable configuration, external IP detection, and hostname validation.
"""

import os
import re
import time
import logging
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


@dataclass
class HostnameResult:
    """Result of hostname resolution with metadata."""
    hostname: str
    detection_method: str  # 'override', 'env_var', 'external_ip', 'request_host', 'fallback'
    is_localhost: bool
    is_external_accessible: bool
    warnings: List[str]
    timestamp: datetime


class HostnameResolver:
    """
    Service for resolving appropriate hostnames for external client connections.
    
    Provides intelligent hostname detection with fallback mechanisms and caching
    for optimal performance and reliability.
    """
    
    # External IP detection services with fallback
    EXTERNAL_IP_SERVICES = [
        'https://api.ipify.org',
        'https://httpbin.org/ip',
        'https://icanhazip.com',
        'https://ifconfig.me/ip'
    ]
    
    # Localhost patterns for validation
    LOCALHOST_PATTERNS = [
        r'^localhost$',
        r'^127\.\d+\.\d+\.\d+$',
        r'^::1$',
        r'^0\.0\.0\.0$'
    ]
    
    def __init__(self):
        """Initialize the hostname resolver with configuration."""
        self._external_ip_cache: Optional[Dict[str, Any]] = None
        self._cache_timeout = int(os.getenv('QR_HOST_DETECTION_TIMEOUT', '300'))  # 5 minutes default
        self._request_timeout = int(os.getenv('QR_HOST_DETECTION_TIMEOUT', '5'))  # 5 seconds default
        self._disable_external_ip = os.getenv('QR_DISABLE_EXTERNAL_IP', 'false').lower() == 'true'
    
    def get_external_hostname(self, request_host: Optional[str] = None, 
                            override_host: Optional[str] = None) -> HostnameResult:
        """
        Get the appropriate hostname for external client connections.
        
        Args:
            request_host: The host from the HTTP request
            override_host: Manual hostname override
            
        Returns:
            HostnameResult with resolved hostname and metadata
        """
        warnings = []
        
        # Priority 1: Manual override parameter
        if override_host:
            is_localhost = self.is_localhost_address(override_host)
            is_valid, validation_msg = self.validate_hostname(override_host)
            
            if not is_valid:
                warnings.append(f"Override hostname validation failed: {validation_msg}")
            
            if is_localhost:
                warnings.append("Override hostname appears to be localhost - may not work for external clients")
            
            return HostnameResult(
                hostname=override_host,
                detection_method='override',
                is_localhost=is_localhost,
                is_external_accessible=not is_localhost and is_valid,
                warnings=warnings,
                timestamp=datetime.now()
            )
        
        # Priority 2: Environment variables
        env_host = os.getenv('EXTERNAL_HOST') or os.getenv('SERVER_HOST')
        if env_host:
            is_localhost = self.is_localhost_address(env_host)
            is_valid, validation_msg = self.validate_hostname(env_host)
            
            if not is_valid:
                warnings.append(f"Environment hostname validation failed: {validation_msg}")
            
            if is_localhost:
                warnings.append("Environment hostname appears to be localhost - may not work for external clients")
            
            return HostnameResult(
                hostname=env_host,
                detection_method='env_var',
                is_localhost=is_localhost,
                is_external_accessible=not is_localhost and is_valid,
                warnings=warnings,
                timestamp=datetime.now()
            )
        
        # Priority 3: External IP detection
        if not self._disable_external_ip:
            try:
                external_ip = self.get_external_ip()
                if external_ip:
                    return HostnameResult(
                        hostname=external_ip,
                        detection_method='external_ip',
                        is_localhost=False,
                        is_external_accessible=True,
                        warnings=warnings,
                        timestamp=datetime.now()
                    )
            except Exception as e:
                logger.warning(f"External IP detection failed: {e}")
                warnings.append(f"External IP detection failed: {str(e)}")
        
        # Priority 4: Request host (if not localhost)
        if request_host:
            # Clean the request host (remove port if present)
            clean_host = request_host.split(':')[0]
            is_localhost = self.is_localhost_address(clean_host)
            
            if not is_localhost:
                is_valid, validation_msg = self.validate_hostname(clean_host)
                if is_valid:
                    return HostnameResult(
                        hostname=clean_host,
                        detection_method='request_host',
                        is_localhost=False,
                        is_external_accessible=True,
                        warnings=warnings,
                        timestamp=datetime.now()
                    )
                else:
                    warnings.append(f"Request host validation failed: {validation_msg}")
            else:
                warnings.append("Request host is localhost - not suitable for external clients")
        
        # Priority 5: Fallback with warning
        fallback_host = request_host.split(':')[0] if request_host else 'localhost'
        warnings.append("Using fallback hostname - QR code may not work for external clients")
        warnings.append("Consider setting EXTERNAL_HOST environment variable or providing server_host parameter")
        
        return HostnameResult(
            hostname=fallback_host,
            detection_method='fallback',
            is_localhost=True,
            is_external_accessible=False,
            warnings=warnings,
            timestamp=datetime.now()
        )
    
    def is_localhost_address(self, hostname: str) -> bool:
        """
        Check if a hostname is a localhost address.
        
        Args:
            hostname: The hostname to check
            
        Returns:
            True if the hostname is a localhost address
        """
        if not hostname:
            return True
        
        hostname = hostname.lower().strip()
        
        for pattern in self.LOCALHOST_PATTERNS:
            if re.match(pattern, hostname):
                return True
        
        return False
    
    def validate_hostname(self, hostname: str) -> Tuple[bool, str]:
        """
        Validate hostname format and accessibility.
        
        Args:
            hostname: The hostname to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not hostname:
            return False, "Hostname is empty"
        
        hostname = hostname.strip()
        
        # Basic format validation
        if len(hostname) > 253:
            return False, "Hostname too long (max 253 characters)"
        
        # Check for invalid characters
        if not re.match(r'^[a-zA-Z0-9.-]+$', hostname):
            return False, "Hostname contains invalid characters"
        
        # Validate IP address format
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
            parts = hostname.split('.')
            try:
                for part in parts:
                    num = int(part)
                    if num < 0 or num > 255:
                        return False, "Invalid IP address format"
            except ValueError:
                return False, "Invalid IP address format"
        
        # Validate domain name format
        elif '.' in hostname:
            labels = hostname.split('.')
            for label in labels:
                if not label:
                    return False, "Empty label in hostname"
                if len(label) > 63:
                    return False, "Label too long in hostname (max 63 characters)"
                if not re.match(r'^[a-zA-Z0-9-]+$', label):
                    return False, "Invalid characters in hostname label"
                if label.startswith('-') or label.endswith('-'):
                    return False, "Hostname label cannot start or end with hyphen"
        
        return True, ""
    
    def get_external_ip(self) -> Optional[str]:
        """
        Detect external IP address using multiple fallback services.
        
        Returns:
            External IP address or None if detection fails
        """
        # Check cache first
        if self._external_ip_cache:
            cache_time = self._external_ip_cache.get('timestamp', datetime.min)
            if datetime.now() - cache_time < timedelta(seconds=self._cache_timeout):
                logger.debug("Using cached external IP")
                return self._external_ip_cache.get('ip')
        
        # Try each service with timeout
        for service_url in self.EXTERNAL_IP_SERVICES:
            try:
                logger.debug(f"Attempting external IP detection via {service_url}")
                response = requests.get(service_url, timeout=self._request_timeout)
                response.raise_for_status()
                
                # Parse response based on service
                if 'httpbin.org' in service_url:
                    # httpbin returns JSON: {"origin": "1.2.3.4"}
                    try:
                        ip = response.json().get('origin', '').split(',')[0].strip()
                    except (ValueError, AttributeError):
                        # Fallback to text parsing if JSON fails
                        ip = response.text.strip()
                else:
                    # Other services return plain text IP
                    ip = response.text.strip()
                
                # Validate the IP
                if self._is_valid_ip(ip):
                    # Cache the result
                    self._external_ip_cache = {
                        'ip': ip,
                        'timestamp': datetime.now(),
                        'service': service_url
                    }
                    logger.info(f"External IP detected: {ip} via {service_url}")
                    return ip
                else:
                    logger.warning(f"Invalid IP received from {service_url}: {ip}")
                    
            except requests.RequestException as e:
                logger.debug(f"External IP detection failed for {service_url}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error with {service_url}: {e}")
                continue
        
        logger.warning("All external IP detection services failed")
        return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """
        Validate IP address format.
        
        Args:
            ip: IP address string to validate
            
        Returns:
            True if valid IP address
        """
        if not ip:
            return False
        
        # Basic IPv4 validation
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
            parts = ip.split('.')
            try:
                for part in parts:
                    num = int(part)
                    if num < 0 or num > 255:
                        return False
                return True
            except ValueError:
                return False
        
        return False
    
    def clear_cache(self):
        """Clear the external IP cache."""
        self._external_ip_cache = None
        logger.debug("External IP cache cleared")