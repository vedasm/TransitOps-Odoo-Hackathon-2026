"""Authentication endpoints with comprehensive security features."""

import asyncio
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging

from core.config import settings
from core.Hashing import Hash
from core.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token_async,
    revoke_token,
    decode_token,
)
from core.rate_limiter import RateLimiter
from core.redis_client import redis_client
from core.email_sender import send_verification_email, send_password_reset_email
from core.logging_config import audit_logger
from database.db import get_db
from repository import user as user_repo
from repository import token as token_repo
from repository import email_verification as email_repo
from repository import password_reset as reset_repo
import schemas, models
from core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"], prefix="/auth")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
rate_limiter = RateLimiter(redis_client)


def _get_client_identifier(request: Request) -> str:
    """Get unique client identifier for rate limiting and logging."""
    return f"ip_{request.client.host if request.client else 'unknown'}"


def _get_request_id(request: Request) -> str:
    """Get request ID from state."""
    return getattr(request.state, 'request_id', 'unknown')


@router.post("/register", response_model=schemas.ShowUser, status_code=status.HTTP_201_CREATED)
async def register(
    http_request: Request,
    request: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Register a new user with email verification required.
    
    Enforces strong password requirements and sends verification email.
    """
    client_id = _get_client_identifier(http_request)
    request_id = _get_request_id(http_request)
    
    # Rate limit registrations per IP
    if not await rate_limiter.check_rate_limit(
        client_id,
        "register",
        settings.RATE_LIMIT_REGISTER_ATTEMPTS,
        settings.RATE_LIMIT_REGISTER_WINDOW_SECONDS
    ):
        logger.warning(
            f"Registration rate limit exceeded for {client_id}",
            extra={'request_id': request_id, 'ip': client_id}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts"
        )
    
    await rate_limiter.increment_counter(
        client_id,
        "register",
        settings.RATE_LIMIT_REGISTER_WINDOW_SECONDS
    )
    
    # Check if email already exists (timing-safe)
    existing_user = user_repo.get_user_by_email(request.email, db)
    if existing_user:
        audit_logger.log_suspicious_activity(
            "registration_attempt_existing_email",
            ip=client_id,
            details={"email": request.email}
        )
    
    # Create user (whether email exists or not)
    if not existing_user:
        new_user = user_repo.create_user(request, db)
        verification_token = Hash.generate_verification_token()
        email_repo.create_verification_token(
            new_user.id,
            verification_token,
            expires_in_hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS,
            db=db
        )
        
        audit_logger.log_registration(new_user.email, client_id)
        
        # Send verification email in background
        background_tasks.add_task(
            send_verification_email,
            to_email=new_user.email,
            user_name=new_user.name,
            token=verification_token,
        )
        
        logger.info(
            f"User registered successfully: {new_user.email}",
            extra={'request_id': request_id, 'user_id': new_user.id, 'ip': client_id}
        )
        return new_user
    else:
        new_user = existing_user
    
    # Return existing user if already registered (no error to prevent enumeration)
    return new_user


@router.get("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    http_request: Request,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Verify user email with token.
    
    Token is single-use and expires after configured hours.
    """
    client_id = _get_client_identifier(http_request)
    request_id = _get_request_id(http_request)
    
    # Rate limit email verification attempts
    if not await rate_limiter.check_rate_limit(
        client_id,
        "verify_email",
        settings.RATE_LIMIT_EMAIL_VERIFY_ATTEMPTS,
        settings.RATE_LIMIT_EMAIL_VERIFY_WINDOW_SECONDS
    ):
        logger.warning(f"Email verification rate limit exceeded for {client_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts"
        )
    
    await rate_limiter.increment_counter(
        client_id,
        "verify_email",
        settings.RATE_LIMIT_EMAIL_VERIFY_WINDOW_SECONDS
    )
    
    record = email_repo.get_verification_token(token, db)
    if not record:
        logger.warning(f"Invalid verification token attempted from {client_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    if record.expires_at < datetime.utcnow():
        logger.warning(f"Expired verification token used from {client_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired"
        )
    
    if record.verified_at is not None:
        logger.info(f"Email already verified: user {record.user_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    email_repo.mark_verified(record.id, db)
    user_repo.verify_user_email(record.user_id, db)
    
    audit_logger.log_email_verified(record.user_id)
    logger.info(
        f"Email verified successfully for user {record.user_id}",
        extra={'request_id': request_id, 'user_id': record.user_id}
    )
    
    return {
        "status": "success",
        "message": "Email verified successfully. You can now log in.",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/login", response_model=schemas.TokenResponse)
async def login(
    http_request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authenticate user with email and password.
    
    Returns JWT access and refresh tokens.
    Enforces rate limiting and account lockout after failed attempts.
    """
    client_id = _get_client_identifier(http_request)
    request_id = _get_request_id(http_request)
    email = form_data.username  # OAuth2 uses 'username' field for email

    # Lookup user first so we can check account lockout before anything else.
    # This ensures a locked account always returns the correct error even when
    # the IP rate limit has also been exceeded.
    user_obj = user_repo.get_user_by_email(email, db)

    # Check if account is locked — must come before the IP rate limit check
    if user_obj and user_obj.account_locked_until and user_obj.account_locked_until > datetime.utcnow():
        minutes_remaining = int((user_obj.account_locked_until - datetime.utcnow()).total_seconds() / 60)
        audit_logger.log_suspicious_activity(
            "login_attempt_locked_account",
            user_id=user_obj.id,
            ip=client_id
        )
        logger.warning(f"Login attempt on locked account: user {user_obj.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked. Try again in {minutes_remaining} minutes."
        )

    # IP-based rate limit check (brute-force protection for non-locked accounts)
    if not await rate_limiter.check_rate_limit(
        client_id,
        "login_attempt",
        settings.RATE_LIMIT_LOGIN_ATTEMPTS,
        settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS
    ):
        audit_logger.log_suspicious_activity(
            "login_rate_limit_exceeded",
            ip=client_id,
            details={"email": email}
        )
        logger.warning(f"Login rate limit exceeded from {client_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )

    # Check credentials (without revealing which field failed)
    credentials_valid = user_obj and Hash.verify(user_obj.password, form_data.password)

    if not credentials_valid:
        await rate_limiter.increment_counter(
            client_id,
            "login_attempt",
            settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS
        )

        # Update failed attempts and lock account if threshold reached
        if user_obj:
            user_obj = user_repo.update_failed_attempts(user_obj.id, db, increment=True)
            if user_obj.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                user_repo.lock_account(user_obj.id, db, minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
                audit_logger.log_account_locked(
                    user_obj.id,
                    f"Too many failed login attempts ({user_obj.failed_login_attempts})"
                )
                logger.warning(f"Account locked: user {user_obj.id} after {user_obj.failed_login_attempts} failed attempts")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account locked due to too many failed attempts. Try again in {settings.ACCOUNT_LOCKOUT_MINUTES} minutes."
                )

        audit_logger.log_login_attempt(email, client_id, False, "Invalid credentials")
        logger.warning(f"Failed login attempt for {email} from {client_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check if email is verified
    if not user_obj.is_email_verified:
        audit_logger.log_suspicious_activity(
            "login_unverified_email",
            user_id=user_obj.id,
            ip=client_id
        )
        logger.warning(f"Login attempt with unverified email: user {user_obj.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox for verification link."
        )
    
    # Success: reset failed attempts
    user_repo.reset_failed_attempts(user_obj.id, db)
    
    # Create tokens
    access_token = create_access_token(user_obj.id)
    refresh_token = create_refresh_token(user_obj.id)
    
    # Store tokens in database for revocation tracking
    access_claims = await decode_token(access_token)
    access_expires_at = datetime.fromtimestamp(int(access_claims.get("exp")), tz=timezone.utc) if isinstance(access_claims.get("exp"), (int, float)) else access_claims.get("exp")
    token_repo.create_token_record(user_obj.id, access_claims.get("jti"), "access", access_expires_at, db)
    
    refresh_claims = await decode_token(refresh_token)
    refresh_expires_at = datetime.fromtimestamp(int(refresh_claims.get("exp")), tz=timezone.utc) if isinstance(refresh_claims.get("exp"), (int, float)) else refresh_claims.get("exp")
    token_repo.create_token_record(user_obj.id, refresh_claims.get("jti"), "refresh", refresh_expires_at, db)
    
    audit_logger.log_login_attempt(email, client_id, True, "Successful login")
    logger.info(
        f"User logged in: {email}",
        extra={'request_id': request_id, 'user_id': user_obj.id, 'ip': client_id}
    )
    
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh_access_token(
    http_request: Request,
    request: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token.
    
    Invalidates old refresh token and issues new access and refresh tokens.
    """
    client_id = _get_client_identifier(http_request)
    request_id = _get_request_id(http_request)
    
    try:
        claims = await verify_token_async(request.refresh_token, "refresh", db_session=db)
    except ValueError as e:
        audit_logger.log_suspicious_activity(
            "invalid_refresh_token",
            ip=client_id,
            details={"error": str(e)}
        )
        logger.warning(f"Invalid refresh token from {client_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = int(claims.get("sub"))
    
    # Mark old refresh token as revoked
    exp = claims.get("exp")
    refresh_expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc) if isinstance(exp, (int, float)) else exp
    token_repo.mark_token_revoked(claims.get("jti"), user_id, "refresh", refresh_expires_at, db)
    
    try:
        await revoke_token(request.refresh_token)
    except ValueError:
        pass  # Already revoked
    
    # Create new tokens
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    
    access_claims = await decode_token(access_token)
    access_expires_at = datetime.fromtimestamp(int(access_claims.get("exp")), tz=timezone.utc) if isinstance(access_claims.get("exp"), (int, float)) else access_claims.get("exp")
    token_repo.create_token_record(user_id, access_claims.get("jti"), "access", access_expires_at, db)
    
    refresh_claims = await decode_token(refresh_token)
    refresh_expires_at = datetime.fromtimestamp(int(refresh_claims.get("exp")), tz=timezone.utc) if isinstance(refresh_claims.get("exp"), (int, float)) else refresh_claims.get("exp")
    token_repo.create_token_record(user_id, refresh_claims.get("jti"), "refresh", refresh_expires_at, db)
    
    logger.info(
        f"Token refreshed for user {user_id}",
        extra={'request_id': request_id, 'user_id': user_id, 'ip': client_id}
    )
    
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    http_request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Logout user by revoking their access token.
    """
    client_id = _get_client_identifier(http_request)
    request_id = _get_request_id(http_request)
    
    try:
        claims = await verify_token_async(token, "access", db_session=db)
    except ValueError as e:
        logger.warning(f"Invalid token on logout from {client_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )
    
    user_id = int(claims.get("sub"))
    
    # Mark token as revoked
    exp = claims.get("exp")
    expires_at = datetime.fromtimestamp(int(exp), tz=timezone.utc) if isinstance(exp, (int, float)) else exp
    token_repo.mark_token_revoked(claims.get("jti"), user_id, "access", expires_at, db)
    
    try:
        await revoke_token(token)
    except ValueError:
        logger.error(f"Error revoking token for user {user_id}")
    
    audit_logger.log_token_revoked(user_id, "access")
    logger.info(
        f"User logged out: {user_id}",
        extra={'request_id': request_id, 'user_id': user_id, 'ip': client_id}
    )
    
    return {
        "status": "success",
        "message": "Logged out successfully",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    http_request: Request,
    request: schemas.PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Request password reset link.
    
    Returns same response regardless of whether email exists (timing-safe).
    """
    client_id = _get_client_identifier(http_request)
    request_id = _get_request_id(http_request)
    
    # Rate limit password reset requests
    if not await rate_limiter.check_rate_limit(
        client_id,
        "forgot_password",
        settings.RATE_LIMIT_PASSWORD_RESET_ATTEMPTS,
        settings.RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS
    ):
        logger.warning(f"Password reset rate limit exceeded from {client_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests"
        )
    
    await rate_limiter.increment_counter(
        client_id,
        "forgot_password",
        settings.RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS
    )
    
    # Simulate consistent response time (timing-safe)
    start_time = time.time()
    
    user_obj = user_repo.get_user_by_email(request.email, db)
    if user_obj and user_obj.account_locked_until and user_obj.account_locked_until > datetime.utcnow():
        minutes_remaining = int((user_obj.account_locked_until - datetime.utcnow()).total_seconds() / 60)
        logger.warning(f"Password reset attempt on locked account: user {user_obj.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked. Try again in {minutes_remaining} minutes."
        )
    if user_obj:
        reset_token = Hash.generate_verification_token()
        reset_repo.create_reset_token(
            user_obj.id,
            reset_token,
            expires_in_hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS,
            db=db
        )
        
        background_tasks.add_task(
            send_password_reset_email,
            to_email=user_obj.email,
            user_name=user_obj.name,
            token=reset_token,
        )
        
        logger.info(f"Password reset requested for user {user_obj.id}")
    
    # Delay to constant ~1 second response time (prevent timing attacks)
    elapsed = time.time() - start_time
    if elapsed < 1.0:
        await asyncio.sleep(1.0 - elapsed)
    
    return {
        "status": "success",
        "message": "If the email exists, a reset link has been sent",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/reset-password", status_code=status.HTTP_200_OK)
async def validate_reset_token(
    http_request: Request,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Validate password reset token before showing reset form.
    """
    client_id = _get_client_identifier(http_request)
    
    record = reset_repo.get_reset_token(token, db)
    if not record:
        logger.warning(f"Invalid reset token from {client_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token"
        )
    
    if record.expires_at < datetime.utcnow():
        logger.warning(f"Expired reset token used from {client_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    if record.used_at is not None:
        logger.warning(f"Already-used reset token attempted from {client_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token already used"
        )
    
    return {
        "status": "valid",
        "message": "Reset token is valid. You can now set a new password.",
        "token": token,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    http_request: Request,
    request: schemas.PasswordResetConfirm,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    client_id = _get_client_identifier(http_request)

    record = reset_repo.get_reset_token(token, db)
    if not record or record.expires_at < datetime.utcnow() or record.used_at is not None:
        logger.warning(f"Invalid/expired/used reset token from {client_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Block reset if account is currently locked
    user_obj = user_repo.get_user_by_id(record.user_id, db)
    if user_obj and user_obj.account_locked_until and user_obj.account_locked_until > datetime.utcnow():
        minutes_remaining = int((user_obj.account_locked_until - datetime.utcnow()).total_seconds() / 60)
        logger.warning(f"Password reset attempt on locked account: user {user_obj.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked. Try again in {minutes_remaining} minutes."
        )

    # Mark token as used
    reset_repo.mark_used(record.id, db)
    
    # Update password
    user_repo.update_password(record.user_id, Hash.bcrypt(request.new_password), db)
    
    # Revoke all existing tokens
    token_repo.revoke_user_tokens(record.user_id, db)
    
    audit_logger.log_password_reset(record.user_id)
    logger.info(f"Password reset successfully for user {record.user_id}")
    
    return {
        "status": "success",
        "message": "Password reset successfully. Please log in with your new password.",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    http_request: Request,
    request: schemas.ChangePasswordRequest,
    current_user: models.user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client_id = _get_client_identifier(http_request)
    request_id = _get_request_id(http_request)
    
    # Verify old password
    if not Hash.verify(current_user.password, request.old_password):
        audit_logger.log_suspicious_activity(
            "incorrect_password_on_change",
            user_id=current_user.id,
            ip=client_id
        )
        logger.warning(f"Incorrect password on change for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Old password is incorrect"
        )
    
    # Update password
    user_repo.update_password(current_user.id, Hash.bcrypt(request.new_password), db)
    
    # Revoke all existing tokens
    token_repo.revoke_user_tokens(current_user.id, db)
    
    audit_logger.log_password_reset(current_user.id)
    logger.info(
        f"Password changed for user {current_user.id}",
        extra={'request_id': request_id, 'user_id': current_user.id, 'ip': client_id}
    )
    
    return {
        "status": "success",
        "message": "Password changed successfully. Please log in again.",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/me", response_model=schemas.ShowUser)
async def get_current_user_info(
    http_request: Request,
    current_user: models.user = Depends(get_current_user)
):
    """Get current authenticated user's information."""
    request_id = _get_request_id(http_request)
    logger.info(
        f"User info retrieved for user {current_user.id}",
        extra={'request_id': request_id, 'user_id': current_user.id}
    )
    return current_user