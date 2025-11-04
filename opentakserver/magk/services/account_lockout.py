#!/usr/bin/env python3
"""
Account Lockout Manager for MAGK-Admin
Prevents credential stuffing attacks by locking accounts after failed attempts
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class AccountLockoutManager:
    """
    Manage account lockouts after failed login attempts.
    
    This class tracks failed login attempts and temporarily locks accounts
    after exceeding the maximum allowed failures. Lockouts automatically
    expire after the configured duration.
    
    Security Features:
    - Tracks failed attempts per username (not per IP)
    - Automatic lockout after max attempts
    - Automatic unlock after lockout duration
    - Reset counter on successful login
    - Admin unlock capability
    - Comprehensive logging
    """
    
    def __init__(self, max_attempts: int = 5, lockout_duration: int = 15):
        """
        Initialize lockout manager.
        
        Args:
            max_attempts: Maximum failed attempts before lockout (default: 5)
            lockout_duration: Lockout duration in minutes (default: 15)
        """
        self.max_attempts = max_attempts
        self.lockout_duration = timedelta(minutes=lockout_duration)
        self.failed_attempts: Dict[str, Tuple[int, datetime]] = {}
        self.locked_accounts: Dict[str, datetime] = {}
        
        logger.info(f"Account lockout initialized: {max_attempts} attempts, {lockout_duration} min lockout")
    
    def is_locked(self, username: str) -> bool:
        """
        Check if account is currently locked.
        
        Args:
            username: Username to check
            
        Returns:
            bool: True if locked, False otherwise
        """
        if username not in self.locked_accounts:
            return False
        
        lock_time = self.locked_accounts[username]
        
        # Check if lockout period has expired
        if datetime.now() - lock_time > self.lockout_duration:
            # Automatically unlock expired lockouts
            del self.locked_accounts[username]
            if username in self.failed_attempts:
                del self.failed_attempts[username]
            logger.info(f"Account auto-unlocked after expiration: {username}")
            return False
        
        return True
    
    def record_failed_attempt(self, username: str) -> int:
        """
        Record a failed login attempt.
        
        Args:
            username: Username that failed authentication
            
        Returns:
            int: Number of failed attempts for this username
        """
        if username not in self.failed_attempts:
            self.failed_attempts[username] = (1, datetime.now())
            logger.info(f"Failed login attempt 1/{self.max_attempts} for: {username}")
            return 1
        
        attempts, first_attempt = self.failed_attempts[username]
        
        # Reset counter if first attempt was more than 1 hour ago
        if datetime.now() - first_attempt > timedelta(hours=1):
            self.failed_attempts[username] = (1, datetime.now())
            logger.info(f"Failed attempt counter reset for: {username}")
            return 1
        
        attempts += 1
        self.failed_attempts[username] = (attempts, first_attempt)
        
        logger.warning(f"Failed login attempt {attempts}/{self.max_attempts} for: {username}")
        
        # Lock account if max attempts reached
        if attempts >= self.max_attempts:
            self.locked_accounts[username] = datetime.now()
            logger.error(f"Account locked due to {attempts} failed attempts: {username}")
        
        return attempts
    
    def reset_attempts(self, username: str):
        """
        Reset failed attempts for successful login.
        
        Args:
            username: Username to reset
        """
        if username in self.failed_attempts:
            del self.failed_attempts[username]
            logger.info(f"Failed attempt counter reset after successful login: {username}")
        
        if username in self.locked_accounts:
            del self.locked_accounts[username]
            logger.info(f"Account unlocked after successful login: {username}")
    
    def get_remaining_attempts(self, username: str) -> int:
        """
        Get remaining login attempts before lockout.
        
        Args:
            username: Username to check
            
        Returns:
            int: Remaining attempts (0 if locked)
        """
        if self.is_locked(username):
            return 0
        
        if username not in self.failed_attempts:
            return self.max_attempts
        
        attempts, _ = self.failed_attempts[username]
        return max(0, self.max_attempts - attempts)
    
    def get_lockout_time_remaining(self, username: str) -> Optional[int]:
        """
        Get remaining lockout time in seconds.
        
        Args:
            username: Username to check
            
        Returns:
            Optional[int]: Seconds remaining, or None if not locked
        """
        if username not in self.locked_accounts:
            return None
        
        lock_time = self.locked_accounts[username]
        elapsed = datetime.now() - lock_time
        remaining = self.lockout_duration - elapsed
        
        if remaining.total_seconds() <= 0:
            # Lockout expired
            return 0
        
        return int(remaining.total_seconds())
    
    def admin_unlock(self, username: str, admin_username: str):
        """
        Manually unlock an account (admin action).
        
        Args:
            username: Username to unlock
            admin_username: Administrator performing the unlock
        """
        if username in self.failed_attempts:
            del self.failed_attempts[username]
        
        if username in self.locked_accounts:
            del self.locked_accounts[username]
        
        logger.warning(f"Account manually unlocked by admin {admin_username}: {username}")
    
    def get_lockout_status(self, username: str) -> dict:
        """
        Get comprehensive lockout status for a username.
        
        Args:
            username: Username to check
            
        Returns:
            dict: Lockout status information
        """
        return {
            'username': username,
            'is_locked': self.is_locked(username),
            'remaining_attempts': self.get_remaining_attempts(username),
            'lockout_time_remaining': self.get_lockout_time_remaining(username),
            'max_attempts': self.max_attempts,
            'lockout_duration_minutes': int(self.lockout_duration.total_seconds() / 60)
        }


# Global instance for use across the application
_lockout_manager = None


def get_lockout_manager(max_attempts: int = 5, lockout_duration: int = 15) -> AccountLockoutManager:
    """
    Get or create the global account lockout manager instance.
    
    Args:
        max_attempts: Maximum failed attempts before lockout
        lockout_duration: Lockout duration in minutes
        
    Returns:
        AccountLockoutManager: Global lockout manager instance
    """
    global _lockout_manager
    
    if _lockout_manager is None:
        _lockout_manager = AccountLockoutManager(max_attempts, lockout_duration)
    
    return _lockout_manager
