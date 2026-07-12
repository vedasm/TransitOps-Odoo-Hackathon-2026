from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship

from app.database.base import Base


class Notification(Base):

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)

    title = Column(String)

    message = Column(String)

    is_read = Column(Boolean, default=False)