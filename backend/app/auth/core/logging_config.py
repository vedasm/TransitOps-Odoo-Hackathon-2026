"""Structured logging configuration for production."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict
import sys


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured logging and log aggregation."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        if hasattr(record, 'endpoint'):
            log_data['endpoint'] = record.endpoint
        if hasattr(record, 'method'):
            log_data['method'] = record.method
            
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """
    Setup structured logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, use JSON formatting; otherwise use standard format
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level))
    
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def get_logger(name: str) -> logging.LoggerAdapter:
    """Get a logger with context support."""
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, {})


class AuditLogger:
    """Specialized logger for authentication and security audit events."""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
    
    def log_login_attempt(self, email: str, ip: str, success: bool, reason: str = ""):
        """Log login attempt."""
        self.logger.info(
            f"Login attempt - email={email}, ip={ip}, success={success}, reason={reason}",
            extra={'event_type': 'login_attempt', 'email': email, 'ip': ip, 'success': success}
        )
    
    def log_registration(self, email: str, ip: str):
        """Log user registration."""
        self.logger.info(
            f"User registration - email={email}, ip={ip}",
            extra={'event_type': 'registration', 'email': email, 'ip': ip}
        )
    
    def log_email_verified(self, user_id: int):
        """Log email verification."""
        self.logger.info(
            f"Email verified - user_id={user_id}",
            extra={'event_type': 'email_verified', 'user_id': user_id}
        )
    
    def log_password_reset(self, user_id: int):
        """Log password reset."""
        self.logger.info(
            f"Password reset - user_id={user_id}",
            extra={'event_type': 'password_reset', 'user_id': user_id}
        )
    
    def log_token_revoked(self, user_id: int, token_type: str):
        """Log token revocation."""
        self.logger.info(
            f"Token revoked - user_id={user_id}, type={token_type}",
            extra={'event_type': 'token_revoked', 'user_id': user_id, 'token_type': token_type}
        )
    
    def log_account_locked(self, user_id: int, reason: str):
        """Log account lockout."""
        self.logger.warning(
            f"Account locked - user_id={user_id}, reason={reason}",
            extra={'event_type': 'account_locked', 'user_id': user_id, 'reason': reason}
        )
    
    def log_suspicious_activity(self, event: str, user_id: int = None, ip: str = None, details: Dict[str, Any] = None):
        """Log suspicious security activity."""
        self.logger.warning(
            f"Suspicious activity detected - event={event}, user_id={user_id}, ip={ip}, details={details}",
            extra={'event_type': 'suspicious_activity', 'user_id': user_id, 'ip': ip}
        )


audit_logger = AuditLogger()
