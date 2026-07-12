import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.database import engine, Base
from app import models 

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError:
        logger.exception(
            "Database is unavailable; skipping table creation at startup."
        )
    yield


app = FastAPI(title="TransitOps API", lifespan=lifespan)


@app.get("/")
def home():
    return {"message": "TransitOps API Running 🚛"}
