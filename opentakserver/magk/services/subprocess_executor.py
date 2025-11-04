#!/usr/bin/env python3
"""
Secure Subprocess Executor for MAGK-Admin
Prevents command injection vulnerabilities in certificate generation and system operations
"""

import subprocess
import logging
import os
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class SecureSubprocessExecutor:
    """
    Secure subprocess execution without shell injection vulnerabilities.
    
    This class provides a safe interface for executing system commands by:
    - Enforcing command whitelisting
    - Using list-based arguments (no shell interpretation)
    - Sanitizing file paths
    - Implementing timeouts
    - Comprehensive error logging
    """
    
    # Whitelist of allowed commands and their permitted subcommands
    ALLOWED_COMMANDS = {
        'openssl': [
            'req',      # Certificate request generation
            'x509',     # Certificate operations
            'ca',       # Certificate authority operations
            'genrsa',   # RSA key generation
            'rsa',      # RSA key operations
            'pkcs12',   # PKCS#12 operations
            'verify',   # Certificate verification
            'version',  # OpenSSL version check
            'list'      # List providers/algorithms
        ]
    }
    
    @staticmethod
    def validate_command(command: str, subcommand: str) -> bool:
        """
        Validate command against whitelist.
        
        Args:
            command: Base command (e.g., 'openssl')
            subcommand: Subcommand (e.g., 'req')
            
        Returns:
            bool: True if command is allowed, False otherwise
        """
        if command not in SecureSubprocessExecutor.ALLOWED_COMMANDS:
            logger.error(f"Command not allowed: {command}")
            return False
        
        if subcommand not in SecureSubprocessExecutor.ALLOWED_COMMANDS[command]:
            logger.error(f"Subcommand not allowed: {command} {subcommand}")
            return False
        
        return True
    
    @staticmethod
    def sanitize_path(path: str, base_directory: str = '/opt/ots/certs') -> str:
        """
        Sanitize file paths to prevent directory traversal attacks.
        
        Args:
            path: User-provided path
            base_directory: Allowed base directory
            
        Returns:
            str: Sanitized absolute path
            
        Raises:
            ValueError: If path is outside allowed directory
        """
        # Resolve to absolute path
        abs_path = os.path.abspath(path)
        allowed_base = os.path.abspath(base_directory)
        
        # Check if path is within allowed directory
        if not abs_path.startswith(allowed_base):
            raise ValueError(f"Path outside allowed directory: {path}")
        
        return abs_path
    
    @staticmethod
    def execute(command_list: List[str], timeout: int = 30) -> Tuple[str, str, int]:
        """
        Safely execute subprocess command without shell injection.
        
        Args:
            command_list: List of command arguments (NOT a string)
            timeout: Command timeout in seconds (default: 30)
            
        Returns:
            tuple: (stdout, stderr, returncode)
            
        Raises:
            ValueError: If command validation fails
            subprocess.TimeoutExpired: If command exceeds timeout
            Exception: If command execution fails
            
        Example:
            >>> executor = SecureSubprocessExecutor()
            >>> stdout, stderr, code = executor.execute([
            ...     'openssl', 'version'
            ... ])
            >>> print(stdout)
            OpenSSL 3.0.2 15 Mar 2022
        """
        try:
            # Validate command list
            if not command_list or len(command_list) < 2:
                raise ValueError("Command list must contain at least command and subcommand")
            
            command = command_list[0]
            subcommand = command_list[1]
            
            # Validate against whitelist
            if not SecureSubprocessExecutor.validate_command(command, subcommand):
                raise ValueError(f"Invalid command: {command} {subcommand}")
            
            # Execute without shell (CRITICAL: shell=False prevents injection)
            result = subprocess.run(
                command_list,
                shell=False,  # NEVER use shell=True
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # Don't raise on non-zero exit
            )
            
            # Log successful execution
            logger.info(f"Executed command: {' '.join(command_list)}")
            
            # Log stderr if present (may contain warnings)
            if result.stderr:
                logger.debug(f"Command stderr: {result.stderr}")
            
            return result.stdout, result.stderr, result.returncode
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"Command timed out after {timeout}s: {command_list}")
            raise
        except ValueError as e:
            logger.error(f"Command validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            raise


# Convenience function for backward compatibility
def secure_subprocess_call(command_list: List[str], timeout: int = 30) -> int:
    """
    Convenience function that mimics subprocess.call() but with security.
    
    Args:
        command_list: List of command arguments
        timeout: Command timeout in seconds
        
    Returns:
        int: Return code from command
        
    Example:
        >>> returncode = secure_subprocess_call(['openssl', 'version'])
        >>> print(returncode)
        0
    """
    executor = SecureSubprocessExecutor()
    stdout, stderr, returncode = executor.execute(command_list, timeout)
    return returncode
