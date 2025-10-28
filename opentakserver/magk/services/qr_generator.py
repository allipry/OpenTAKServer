#!/usr/bin/env python3
"""
QR Code Generator Service Module
Handles WiFi QR code string generation for event WiFi networks
"""

import logging

logger = logging.getLogger(__name__)


def generate_wifi_qr_string(ssid: str, password: str, security: str = 'WPA') -> str:
    """
    Generate WiFi QR code string in standard format.
    
    Format: WIFI:T:<security>;S:<ssid>;P:<password>;H:false;;
    
    Args:
        ssid: WiFi network SSID (max 32 characters)
        password: WiFi network password (8-63 characters for WPA/WPA2)
        security: Security type (WPA, WEP, or nopass for open networks)
    
    Returns:
        str: WiFi QR code string in standard format
    
    Raises:
        ValueError: If SSID or password are invalid
    
    Example:
        >>> generate_wifi_qr_string("EventNetwork", "SecurePass123")
        'WIFI:T:WPA;S:EventNetwork;P:SecurePass123;H:false;;'
    """
    # Validate inputs
    if not ssid or not isinstance(ssid, str):
        raise ValueError("SSID must be a non-empty string")
    
    if len(ssid) > 32:
        raise ValueError("SSID must be 32 characters or less")
    
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string")
    
    if security.upper() in ['WPA', 'WPA2'] and (len(password) < 8 or len(password) > 63):
        raise ValueError("WPA/WPA2 password must be between 8 and 63 characters")
    
    # Normalize security type
    security = security.upper()
    if security not in ['WPA', 'WPA2', 'WEP', 'nopass']:
        logger.warning(f"Unknown security type '{security}', defaulting to WPA")
        security = 'WPA'
    
    # Escape special characters in SSID and password
    # Special characters that need escaping: \ ; , : "
    ssid_escaped = _escape_wifi_string(ssid)
    password_escaped = _escape_wifi_string(password)
    
    # Generate WiFi QR string
    # Format: WIFI:T:<security>;S:<ssid>;P:<password>;H:<hidden>;;
    # H:false means network is not hidden
    qr_string = f"WIFI:T:{security};S:{ssid_escaped};P:{password_escaped};H:false;;"
    
    logger.info(f"Generated WiFi QR string for SSID: {ssid}")
    
    return qr_string


def _escape_wifi_string(text: str) -> str:
    """
    Escape special characters in WiFi QR code strings.
    
    Special characters that need escaping: \ ; , : "
    
    Args:
        text: String to escape
    
    Returns:
        str: Escaped string
    """
    # Order matters: escape backslash first
    text = text.replace('\\', '\\\\')
    text = text.replace(';', '\\;')
    text = text.replace(',', '\\,')
    text = text.replace(':', '\\:')
    text = text.replace('"', '\\"')
    
    return text


def validate_wifi_credentials(ssid: str, password: str, security: str = 'WPA') -> tuple[bool, str]:
    """
    Validate WiFi credentials for QR code generation.
    
    Args:
        ssid: WiFi network SSID
        password: WiFi network password
        security: Security type
    
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Validate SSID
        if not ssid or not isinstance(ssid, str):
            return False, "SSID must be a non-empty string"
        
        if len(ssid) > 32:
            return False, "SSID must be 32 characters or less"
        
        # Validate password
        if not password or not isinstance(password, str):
            return False, "Password must be a non-empty string"
        
        # Validate password length for WPA/WPA2
        security_upper = security.upper()
        if security_upper in ['WPA', 'WPA2']:
            if len(password) < 8:
                return False, "WPA/WPA2 password must be at least 8 characters"
            if len(password) > 63:
                return False, "WPA/WPA2 password must be 63 characters or less"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Error validating WiFi credentials: {e}")
        return False, str(e)
