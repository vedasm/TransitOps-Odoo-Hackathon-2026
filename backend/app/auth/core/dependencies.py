from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import logging

from app.auth.core.jwt_handler import verify_token, verify_token_async
from app.auth.core.redis_client import redis_client
from app.auth.core.rate_limiter import RateLimiter
from app.database.base import get_db
from app.auth.repository import user as user_repo
from app.auth import models

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
rate_limiter = RateLimiter(redis_client)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    try:
        # Pass db_session for database token revocation check
        claims = await verify_token_async(token, "access", db_session=db)
    except ValueError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
        )

    try:
        user_id = int(claims.get("sub"))
    except Exception:
        logger.error(f"Invalid token subject: {claims.get('sub')}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user_obj = user_repo.get_user_by_id(user_id, db)
    if not user_obj:
        logger.warning(f"User not found: {user_id}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user_obj


async def verify_rate_limit(request: Request, action: str, limit: int, window_seconds: int):
    """Verify and increment rate limit counter."""
    identifier = f"ip_{request.client.host if request.client else 'unknown'}"
    if not await rate_limiter.check_rate_limit(identifier, action, limit, window_seconds):
        logger.warning(f"Rate limit exceeded: {action} for {identifier}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
    await rate_limiter.increment_counter(identifier, action, window_seconds)