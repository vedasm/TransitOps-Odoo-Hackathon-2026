from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class Driver(Base):

    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True)

    name = Column(String(100))

    license_number = Column(String(50), unique=True)

    license_category = Column(String(20))

    license_expiry = Column(String(20))

    contact_number = Column(String(20))

    safety_score = Column(Float, default=100)

    status = Column(String(20), default="Available")
