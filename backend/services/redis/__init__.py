import aioredis

REDIS_URL = "redis://localhost:6379"

redis_client = aioredis.Redis.from_url(
    REDIS_URL,
    decode_response=True
)

