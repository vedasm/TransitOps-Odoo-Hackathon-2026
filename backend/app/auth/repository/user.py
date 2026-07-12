from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.auth.core.Hashing import Hash
from app import models, schemas

def create_user(request: schemas.UserCreate, db: Session):
    new_user = models.User(
        name=request.name,
        email=request.email,
        password=Hash.bcrypt(request.password),
        is_email_verified=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_user_by_email(email: str, db: Session) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_id(user_id: int, db: Session) -> models.User | None:
    return db.query(models.User).filter(models.User.id == user_id).first()

def update_failed_attempts(user_id: int, db: Session, increment: bool = True) -> models.User:
    user_obj = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_obj:
        raise ValueError("User not found")
    user_obj.failed_login_attempts = user_obj.failed_login_attempts + 1 if increment else 0
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

def reset_failed_attempts(user_id: int, db: Session) -> models.User:
    return update_failed_attempts(user_id, db, increment=False)

def lock_account(user_id: int, db: Session, minutes: int = 30) -> models.User:
    user_obj = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_obj:
        raise ValueError("User not found")
    user_obj.account_locked_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

def unlock_account(user_id: int, db: Session) -> models.User:
    user_obj = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_obj:
        raise ValueError("User not found")
    user_obj.account_locked_until = None
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

def verify_user_email(user_id: int, db: Session) -> models.User:
    user_obj = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_obj:
        raise ValueError("User not found")
    user_obj.is_email_verified = True
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj

def update_password(user_id: int, new_hashed_password: str, db: Session) -> models.User:
    user_obj = db.query(models.User).filter(models.User.id == user_id).first()
    if not user_obj:
        raise ValueError("User not found")
    user_obj.password = new_hashed_password
    db.add(user_obj)
    db.commit()
    db.refresh(user_obj)
    return user_obj
