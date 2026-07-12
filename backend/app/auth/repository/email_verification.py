from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import models

def create_verification_token(user_id: int, token: str, expires_in_hours: int, db: Session):
    record = models.EmailVerificationToken(
        user_id=user_id,
        verification_token=token,
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

def get_verification_token(token: str, db: Session):
    return db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.verification_token == token
    ).first()

def mark_verified(verification_id: int, db: Session):
    record = db.query(models.EmailVerificationToken).filter(models.EmailVerificationToken.id == verification_id).first()
    if not record:
        raise ValueError("Verification record not found")
    record.verified_at = datetime.now(timezone.utc)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record