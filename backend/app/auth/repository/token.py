from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app import models


def is_token_revoked(jti: str, db: Session) -> bool:
    """Check if a token is revoked. Returns True if revoked, False if valid or not found."""
    token = db.query(models.Token).filter(models.Token.token_jti == jti).first()
    # Token is revoked if: it exists AND has a revoked_at timestamp
    return token is not None and token.revoked_at is not None


def create_revoked_token(user_id: int, jti: str, token_type: str, expires_at: datetime, db: Session):
    token = models.Token(
        user_id=user_id,
        token_jti=jti,
        token_type=token_type,
        revoked_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def revoke_user_tokens(user_id: int, db: Session):
    now = datetime.now(timezone.utc)
    tokens = db.query(models.Token).filter(models.Token.user_id == user_id, models.Token.revoked_at == None).all()
    for token in tokens:
        token.revoked_at = now
    db.add_all(tokens)
    db.commit()
    return tokens


def create_token_record(user_id: int, jti: str, token_type: str, expires_at: datetime, db: Session):
    """Create a token record for an issued token (not revoked)."""
    token = models.Token(
        user_id=user_id,
        token_jti=jti,
        token_type=token_type,
        revoked_at=None,
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def mark_token_revoked(jti: str, user_id: int, token_type: str, expires_at: datetime, db: Session):
    """Mark an existing token as revoked, or create a revoked record if missing."""
    token = db.query(models.Token).filter(models.Token.token_jti == jti).first()
    if token:
        token.revoked_at = datetime.now(timezone.utc)
        db.add(token)
        db.commit()
        db.refresh(token)
        return token

    token = models.Token(
        user_id=user_id,
        token_jti=jti,
        token_type=token_type,
        revoked_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    return token
