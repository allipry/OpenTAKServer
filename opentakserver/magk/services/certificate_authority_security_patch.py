#!/usr/bin/env python3
"""
Security patch for certificate_authority.py
This module provides secure wrappers for certificate operations
"""

import shlex
from typing import List
from .subprocess_executor import SecureSubprocessExecutor

# Initialize the secure executor
executor = SecureSubprocessExecutor()


def parse_openssl_command(command_string: str) -> List[str]:
    """
    Parse an OpenSSL command string into a safe list format.
    
    This function takes a shell command string and converts it to a list
    of arguments suitable for secure subprocess execution.
    
    Args:
        command_string: Shell command string (e.g., "openssl req -new ...")
        
    Returns:
        List[str]: Command arguments as list
        
    Example:
        >>> cmd = "openssl req -new -x509 -days 3650"
        >>> parse_openssl_command(cmd)
        ['openssl', 'req', '-new', '-x509', '-days', '3650']
    """
    # Use shlex to properly parse the command while preserving quoted strings
    return shlex.split(command_string)


def secure_openssl_call(command_string: str, timeout: int = 30) -> int:
    """
    Securely execute an OpenSSL command.
    
    This function replaces subprocess.call(command, shell=True) with
    a secure implementation that prevents command injection.
    
    Args:
        command_string: OpenSSL command as string
        timeout: Command timeout in seconds
        
    Returns:
        int: Return code from command
        
    Example:
        >>> returncode = secure_openssl_call("openssl version")
        >>> print(returncode)
        0
    """
    # Parse command string to list
    command_list = parse_openssl_command(command_string)
    
    # Execute securely
    stdout, stderr, returncode = executor.execute(command_list, timeout)
    
    return returncode


# Example of how to convert vulnerable code:
#
# BEFORE (VULNERABLE):
# command = 'openssl req -new -x509 -days 3650 -keyout key.pem -out cert.pem'
# exit_code = subprocess.call(command, shell=True)
#
# AFTER (SECURE):
# from opentakserver.magk.services.certificate_authority_security_patch import secure_openssl_call
# command = 'openssl req -new -x509 -days 3650 -keyout key.pem -out cert.pem'
# exit_code = secure_openssl_call(command)
