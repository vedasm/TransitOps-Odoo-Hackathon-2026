from sqlalchemy import Column, Integer, Float, ForeignKey
from app.database import Base


class FuelLog(Base):

    __tablename__ = "fuel_logs"

    id = Column(Integer, primary_key=True)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    liters = Column(Float)

    cost = Column(Float)
