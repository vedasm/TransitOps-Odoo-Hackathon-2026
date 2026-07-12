"""Password and input validators for production security."""

import re
from pydantic import field_validator, BaseModel
from typing import Annotated
from pydantic import StringConstraints


class PasswordValidator:
    """Validates password strength according to OWASP standards."""
    
    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    
    SPECIAL_CHARS = r"[@$!%*?&\-_+=#^~]"
    
    @staticmethod
    def validate(password: str) -> tuple[bool, str]:
        """
        Validate password strength.
        Returns: (is_valid, error_message)
        """
        if len(password) < PasswordValidator.MIN_LENGTH:
            return False, f"Password must be at least {PasswordValidator.MIN_LENGTH} characters long"
        
        if PasswordValidator.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        
        if PasswordValidator.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        
        if PasswordValidator.REQUIRE_DIGIT and not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        
        if PasswordValidator.REQUIRE_SPECIAL and not re.search(PasswordValidator.SPECIAL_CHARS, password):
            return False, f"Password must contain at least one special character from: {PasswordValidator.SPECIAL_CHARS}"
        
        return True, ""
    
    @staticmethod
    def validate_strict(password: str) -> None:
        """Raise exception if password is invalid."""
        is_valid, error_msg = PasswordValidator.validate(password)
        if not is_valid:
            raise ValueError(error_msg)


def validate_password_field(v: str) -> str:
    """Pydantic field validator for passwords."""
    is_valid, error_msg = PasswordValidator.validate(v)
    if not is_valid:
        raise ValueError(error_msg)
    return v


def validate_secret_key(v: str) -> str:
    """Validate JWT SECRET_KEY has minimum cryptographic strength."""
    if len(v) < 64:
        raise ValueError("SECRET_KEY must be at least 64 characters for cryptographic security")
    if not any(c.isdigit() for c in v):
        raise ValueError("SECRET_KEY must contain at least one digit")
    if not any(c.isupper() for c in v):
        raise ValueError("SECRET_KEY must contain at least one uppercase letter")
    if not any(c.islower() for c in v):
        raise ValueError("SECRET_KEY must contain at least one lowercase letter")
    return v
