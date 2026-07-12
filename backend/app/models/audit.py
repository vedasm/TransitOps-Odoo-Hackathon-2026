from sqlalchemy import Column, Integer, String
from app.database import Base


class AuditLog(Base):

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)

    entity = Column(String)

    action = Column(String)
