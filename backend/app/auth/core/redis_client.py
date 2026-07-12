import redis.asyncio as redis

try:
    from app.auth.core.config import settings
except ModuleNotFoundError:
    from core.config import settings

redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)
