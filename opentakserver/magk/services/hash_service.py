#!/usr/bin/env python3
"""
Secure Hash Service for MAGK-Admin
Replaces weak MD5 hashing with SHA-256 for security-sensitive operations
"""

import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SecureHasher:
    """
    Secure hashing utilities - NO MD5 for security purposes.
    
    This class provides secure hashing methods using SHA-256 instead of
    the cryptographically broken MD5 algorithm. MD5 is vulnerable to
    collision attacks and should not be used for security-sensitive operations.
    
    Security Note:
    - Flask-Security password hashing (argon2id) is NOT affected by this change
    - This only affects file integrity verification and data package hashing
    - TAK protocol compatibility is maintained
    """
    
    @staticmethod
    def hash_file(file_path: str) -> str:
        """
        Generate SHA-256 hash of file.
        
        Reads file in chunks to handle large files efficiently without
        loading the entire file into memory.
        
        Args:
            file_path: Path to file to hash
            
        Returns:
            str: Hexadecimal SHA-256 hash string
            
        Example:
            >>> hasher = SecureHasher()
            >>> file_hash = hasher.hash_file('/path/to/file.zip')
            >>> print(file_hash)
            'a3c5f8e9b2d1...'
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Read file in 4KB chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            hash_value = sha256_hash.hexdigest()
            logger.debug(f"Generated SHA-256 hash for file: {file_path}")
            return hash_value
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except PermissionError:
            logger.error(f"Permission denied reading file: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}")
            raise
    
    @staticmethod
    def hash_data(data: bytes) -> str:
        """
        Generate SHA-256 hash of data.
        
        Args:
            data: Bytes to hash
            
        Returns:
            str: Hexadecimal SHA-256 hash string
            
        Example:
            >>> hasher = SecureHasher()
            >>> data_hash = hasher.hash_data(b'Hello, World!')
            >>> print(data_hash)
            'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
        """
        if not isinstance(data, bytes):
            raise TypeError("Data must be bytes, not {}".format(type(data).__name__))
        
        hash_value = hashlib.sha256(data).hexdigest()
        logger.debug(f"Generated SHA-256 hash for {len(data)} bytes of data")
        return hash_value
    
    @staticmethod
    def hash_string(text: str) -> str:
        """
        Generate SHA-256 hash of string.
        
        Args:
            text: String to hash
            
        Returns:
            str: Hexadecimal SHA-256 hash string
            
        Example:
            >>> hasher = SecureHasher()
            >>> text_hash = hasher.hash_string('Hello, World!')
            >>> print(text_hash)
            'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
        """
        if not isinstance(text, str):
            raise TypeError("Text must be string, not {}".format(type(text).__name__))
        
        hash_value = hashlib.sha256(text.encode('utf-8')).hexdigest()
        logger.debug(f"Generated SHA-256 hash for string of length {len(text)}")
        return hash_value
    
    @staticmethod
    def verify_hash(data: bytes, expected_hash: str) -> bool:
        """
        Verify data matches expected hash.
        
        Args:
            data: Data to verify
            expected_hash: Expected SHA-256 hash (hexadecimal)
            
        Returns:
            bool: True if hash matches, False otherwise
            
        Example:
            >>> hasher = SecureHasher()
            >>> data = b'Hello, World!'
            >>> expected = 'dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f'
            >>> hasher.verify_hash(data, expected)
            True
        """
        if not isinstance(data, bytes):
            raise TypeError("Data must be bytes, not {}".format(type(data).__name__))
        
        actual_hash = SecureHasher.hash_data(data)
        matches = actual_hash.lower() == expected_hash.lower()
        
        if matches:
            logger.debug("Hash verification successful")
        else:
            logger.warning("Hash verification failed")
        
        return matches
    
    @staticmethod
    def verify_file_hash(file_path: str, expected_hash: str) -> bool:
        """
        Verify file matches expected hash.
        
        Args:
            file_path: Path to file to verify
            expected_hash: Expected SHA-256 hash (hexadecimal)
            
        Returns:
            bool: True if hash matches, False otherwise
            
        Example:
            >>> hasher = SecureHasher()
            >>> expected = 'a3c5f8e9b2d1...'
            >>> hasher.verify_file_hash('/path/to/file.zip', expected)
            True
        """
        actual_hash = SecureHasher.hash_file(file_path)
        matches = actual_hash.lower() == expected_hash.lower()
        
        if matches:
            logger.info(f"File hash verification successful: {file_path}")
        else:
            logger.warning(f"File hash verification failed: {file_path}")
        
        return matches


class LegacyHasher:
    """
    Legacy MD5 hashing for non-security purposes only.
    
    WARNING: MD5 is cryptographically broken and MUST NOT be used for
    security-sensitive operations. This class is provided only for
    compatibility with systems that require MD5 for non-security purposes.
    
    Use SecureHasher for all security-sensitive operations.
    """
    
    @staticmethod
    def md5_hash_file(file_path: str) -> str:
        """
        Generate MD5 hash of file (NON-SECURITY USE ONLY).
        
        Args:
            file_path: Path to file to hash
            
        Returns:
            str: Hexadecimal MD5 hash string
            
        Warning:
            MD5 is cryptographically broken. Use only for non-security purposes.
        """
        # Explicitly mark as not for security
        md5_hash = hashlib.md5(usedforsecurity=False)
        
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                md5_hash.update(byte_block)
        
        logger.warning(f"Using MD5 hash (non-security) for file: {file_path}")
        return md5_hash.hexdigest()
    
    @staticmethod
    def md5_hash_data(data: bytes) -> str:
        """
        Generate MD5 hash of data (NON-SECURITY USE ONLY).
        
        Args:
            data: Bytes to hash
            
        Returns:
            str: Hexadecimal MD5 hash string
            
        Warning:
            MD5 is cryptographically broken. Use only for non-security purposes.
        """
        logger.warning("Using MD5 hash (non-security) for data")
        return hashlib.md5(data, usedforsecurity=False).hexdigest()


# Convenience functions for backward compatibility
def secure_file_hash(file_path: str) -> str:
    """Generate SHA-256 hash of file (convenience function)"""
    return SecureHasher.hash_file(file_path)


def secure_data_hash(data: bytes) -> str:
    """Generate SHA-256 hash of data (convenience function)"""
    return SecureHasher.hash_data(data)


def secure_string_hash(text: str) -> str:
    """Generate SHA-256 hash of string (convenience function)"""
    return SecureHasher.hash_string(text)
