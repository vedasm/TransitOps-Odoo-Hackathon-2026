from datetime import datetime, timedelta, timezone
import secrets
from typing import Any
from jose import JWTError, jwt
from core.config import settings
from core.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS

def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": secrets.token_urlsafe(32),  # Increased to 256-bit tokens
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(user_id: int) -> str:
    return _create_token(
        subject=str(user_id),
        token_type="access",
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

def create_refresh_token(user_id: int) -> str:
    return _create_token(
        subject=str(user_id),
        token_type="refresh",
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )

def verify_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise ValueError("Token type mismatch")

    return payload


async def verify_token_async(token: str, expected_type: str, db_session=None) -> dict[str, Any]:
    """
    Validate signature, type, expiration, and check JTI revocation in Redis AND database.
    Uses database as authoritative source with Redis as cache fallback.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise ValueError("Token type mismatch")

    jti = payload.get("jti")
    if jti:
        # Check if token is revoked (try database first, fall back to Redis)
        if await _is_jti_revoked(jti, db_session):
            logger.warning(f"Attempt to use revoked token: {jti}")
            raise ValueError("Token has been revoked")

    return payload

async def decode_token(token: str, expected_type: str | None = None, validate_jti: bool = False, db_session=None) -> dict[str, Any]:
    try:
        claims = jwt.get_unverified_claims(token)
    except Exception as exc:
        raise ValueError("Invalid token") from exc

    exp = claims.get("exp")
    if exp is not None:
        if isinstance(exp, (int, float)):
            exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        elif isinstance(exp, datetime):
            exp_dt = exp
        else:
            raise ValueError("Invalid 'exp' claim in token")

        if exp_dt < datetime.now(timezone.utc):
            raise ValueError("Token has expired")

    if expected_type and claims.get("type") != expected_type:
        raise ValueError("Token type mismatch")

    if validate_jti:
        jti = claims.get("jti")
        if jti and await _is_jti_revoked(jti, db_session):
            raise ValueError("Token has been revoked")

    return claims

async def _is_jti_revoked(jti: str | None, db_session=None) -> bool:
    """
    Check if JTI is revoked. First checks Redis (fast), then database (authoritative).
    Returns True if revoked, False if valid.
    """
    if not jti:
        return False
    
    # Check Redis cache first (fastest)
    revoked_key = f"revoked_jti:{jti}"
    if await redis_client.exists(revoked_key) == 1:
        return True
    
    # Check database as authoritative source
    if db_session is not None:
        try:
            from repository import token as token_repo
            is_revoked = token_repo.is_token_revoked(jti, db_session)
            
            # If revoked, cache in Redis for next 24 hours
            if is_revoked:
                await redis_client.setex(revoked_key, 86400, "1")
            
            return is_revoked
        except Exception as e:
            logger.error(f"Error checking token revocation in database: {e}")
            # If database check fails, assume valid (fail open)
            return False
    
    return False

async def revoke_token_jti(jti: str, expires_seconds: int) -> None:
    """Store revoked JTI in Redis."""
    revoked_key = f"revoked_jti:{jti}"
    await redis_client.setex(revoked_key, expires_seconds, "1")

async def revoke_token(token: str) -> None:
    """Revoke a token immediately."""
    try:
        claims = jwt.get_unverified_claims(token)
    except Exception as exc:
        raise ValueError("Invalid token") from exc

    jti = claims.get("jti")
    if not isinstance(jti, str):
        raise ValueError("Token is missing jti")

    exp = claims.get("exp")
    if exp is None:
        raise ValueError("Token is missing exp")

    if isinstance(exp, (int, float)):
        ttl = int(exp - datetime.now(timezone.utc).timestamp())
    elif isinstance(exp, datetime):
        ttl = int((exp - datetime.now(timezone.utc)).total_seconds())
    else:
        raise ValueError("Invalid 'exp' claim in token")

    if ttl <= 0:
        raise ValueError("Token is already expired")

    await revoke_token_jti(jti, ttl)
    logger.info(f"Token revoked: {jti}")
