from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class Maintenance(Base):

    __tablename__ = "maintenance"

    id = Column(Integer, primary_key=True)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    description = Column(String)

    status = Column(String(20), default="Open")
