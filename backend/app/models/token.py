from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_jti = Column(String(255), unique=True, nullable=False, index=True)
    token_type = Column(String(50), nullable=False) # 'access' or 'refresh'
    revoked_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User")
