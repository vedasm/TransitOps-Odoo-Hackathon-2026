from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class Vehicle(Base):

    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True)

    registration_number = Column(String(30), unique=True)

    vehicle_name = Column(String(100))

    vehicle_type = Column(String(50))

    maximum_load_capacity = Column(Float)

    odometer = Column(Float)

    acquisition_cost = Column(Float)

    status = Column(String(20), default="Available")
