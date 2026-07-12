from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import models

def create_reset_token(user_id: int, token: str, expires_in_hours: int, db: Session):
    record = models.PasswordResetToken(
        user_id=user_id,
        reset_token=token,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def get_reset_token(token: str, db: Session):
    return db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.reset_token == token
    ).first()

def mark_used(reset_id: int, db: Session):
    record = db.query(models.PasswordResetToken).filter(models.PasswordResetToken.id == reset_id).first()
    if not record:
        raise ValueError("Reset token not found")
    record.used_at = datetime.now(timezone.utc)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record