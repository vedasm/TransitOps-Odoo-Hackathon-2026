from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship

from app.database.base import Base


class FuelLog(Base):

    __tablename__ = "fuel_logs"

    id = Column(Integer, primary_key=True)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    liters = Column(float)

    cost = Column(float)

class Expense(Base):

    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    expense_type = Column(String(50))

    amount = Column(float)

class Maintenance(Base):

    __tablename__ = "maintenance"

    id = Column(Integer, primary_key=True)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    description = Column(String)

    status = Column(String(20), default="Open")

class Trip(Base):

    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)

    source = Column(String(150))

    destination = Column(String(150))

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    driver_id = Column(Integer, ForeignKey("drivers.id"))

    cargo_weight = Column(float)

    planned_distance = Column(float)

    actual_distance = Column(float)

    fuel_consumed = Column(float)

    status = Column(String(20), default="Draft")

    vehicle = relationship("Vehicle")

    driver = relationship("Driver")