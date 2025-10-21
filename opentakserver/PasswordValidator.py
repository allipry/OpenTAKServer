import typing as t
import re

from flask_security import PasswordUtil


# Common passwords to prevent (top 100 most common passwords)
COMMON_PASSWORDS = {
    'password', '123456', '12345678', 'qwerty', 'abc123', 'monkey', '1234567', 'letmein',
    'trustno1', 'dragon', 'baseball', 'iloveyou', 'master', 'sunshine', 'ashley', 'bailey',
    'passw0rd', 'shadow', '123123', '654321', 'superman', 'qazwsx', 'michael', 'football',
    'password1', 'password123', 'admin', 'admin123', 'root', 'toor', 'pass', 'test',
    'guest', 'welcome', 'login', 'changeme', 'secret', 'default', 'user', 'demo'
}


class PasswordValidator(PasswordUtil):
    """
    Enhanced password validator with comprehensive security policy:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    - No common passwords
    - No @ or : characters (for RTSP compatibility)
    """
    
    MIN_LENGTH = 12
    
    def validate(self, password: str, is_register: bool, **kwargs: t.Any) -> t.Tuple[t.Optional[t.List], str]:
        errors = []
        
        # Check minimum length
        if len(password) < self.MIN_LENGTH:
            errors.append(f"Password must be at least {self.MIN_LENGTH} characters long")
        
        # Check for uppercase letter
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Check for lowercase letter
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Check for number
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        # Check for special character (excluding @ and :)
        if not re.search(r'[!#$%&\'()*+,\-./<=>?[\\\]^_`{|}~]', password):
            errors.append("Password must contain at least one special character (!#$%&*-_+=?)")
        
        # Check for @ or : (RTSP compatibility)
        if '@' in password or ':' in password:
            errors.append("Password cannot contain @ or : characters (RTSP compatibility)")
        
        # Check against common passwords
        if password.lower() in COMMON_PASSWORDS:
            errors.append("Password is too common. Please choose a more secure password")
        
        # Check for sequential characters (e.g., 123, abc)
        if self._has_sequential_chars(password):
            errors.append("Password contains sequential characters. Please choose a more complex password")
        
        # Check for repeated characters (e.g., aaa, 111)
        if self._has_repeated_chars(password):
            errors.append("Password contains too many repeated characters")
        
        if errors:
            return errors, password
        
        # Call parent validation for any additional Flask-Security checks
        return super().validate(password, is_register, **kwargs)
    
    def _has_sequential_chars(self, password: str) -> bool:
        """Check for 3+ sequential characters (123, abc, etc.)"""
        password_lower = password.lower()
        for i in range(len(password_lower) - 2):
            # Check for sequential numbers
            if password_lower[i:i+3].isdigit():
                if int(password_lower[i+1]) == int(password_lower[i]) + 1 and \
                   int(password_lower[i+2]) == int(password_lower[i+1]) + 1:
                    return True
            # Check for sequential letters
            elif password_lower[i:i+3].isalpha():
                if ord(password_lower[i+1]) == ord(password_lower[i]) + 1 and \
                   ord(password_lower[i+2]) == ord(password_lower[i+1]) + 1:
                    return True
        return False
    
    def _has_repeated_chars(self, password: str) -> bool:
        """Check for 3+ repeated characters (aaa, 111, etc.)"""
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                return True
        return False
    
    def get_password_strength(self, password: str) -> dict:
        """
        Calculate password strength score (0-100)
        Returns dict with score and feedback
        """
        score = 0
        feedback = []
        
        # Length score (up to 30 points)
        length = len(password)
        if length >= 12:
            score += min(30, (length - 12) * 2 + 20)
        else:
            score += length * 1.5
        
        # Character variety score (up to 40 points)
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!#$%&\'()*+,\-./<=>?[\\\]^_`{|}~]', password))
        
        variety_score = sum([has_upper, has_lower, has_digit, has_special]) * 10
        score += variety_score
        
        # Complexity bonus (up to 30 points)
        unique_chars = len(set(password))
        complexity_ratio = unique_chars / len(password) if password else 0
        score += complexity_ratio * 30
        
        # Penalties
        if password.lower() in COMMON_PASSWORDS:
            score = max(0, score - 50)
            feedback.append("Common password detected")
        
        if self._has_sequential_chars(password):
            score = max(0, score - 20)
            feedback.append("Contains sequential characters")
        
        if self._has_repeated_chars(password):
            score = max(0, score - 15)
            feedback.append("Contains repeated characters")
        
        # Determine strength level
        if score >= 80:
            strength = "strong"
            feedback.insert(0, "Strong password")
        elif score >= 60:
            strength = "good"
            feedback.insert(0, "Good password")
        elif score >= 40:
            strength = "fair"
            feedback.insert(0, "Fair password - consider making it stronger")
        else:
            strength = "weak"
            feedback.insert(0, "Weak password - please strengthen it")
        
        return {
            "score": int(score),
            "strength": strength,
            "feedback": feedback
        }
