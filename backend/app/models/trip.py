from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Trip(Base):

    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)

    source = Column(String(150))

    destination = Column(String(150))

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    driver_id = Column(Integer, ForeignKey("drivers.id"))

    cargo_weight = Column(Float)

    planned_distance = Column(Float)

    actual_distance = Column(Float)

    fuel_consumed = Column(Float)

    status = Column(String(20), default="Draft")

    vehicle = relationship("Vehicle")

    driver = relationship("Driver")
