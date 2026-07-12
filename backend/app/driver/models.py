from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship

from app.database.base import Base

class Vehicle(Base):

    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True)

    registration_number = Column(String(30), unique=True)

    vehicle_name = Column(String(100))

    vehicle_type = Column(String(50))

    maximum_load_capacity = Column(float)

    odometer = Column(float)

    acquisition_cost = Column(float)

    status = Column(String(20), default="Available")

class Driver(Base):

    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True)

    name = Column(String(100))

    license_number = Column(String(50), unique=True)

    license_category = Column(String(20))

    license_expiry = Column(String(20))

    contact_number = Column(String(20))

    safety_score = Column(float, default=100)

    status = Column(String(20), default="Available")

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

class AuditLog(Base):

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)

    entity = Column(String)

    action = Column(String)