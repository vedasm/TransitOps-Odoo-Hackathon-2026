from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base


class Expense(Base):

    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True)

    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))

    expense_type = Column(String(50))

    amount = Column(Float)
