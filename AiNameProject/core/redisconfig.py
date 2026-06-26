import asyncio
import redis.asyncio as asyncios


REDIS_URL = "redis://127.0.0.1:6379/0"

redis_client = asyncios.from_url(REDIS_URL, encoding="utf-8",decode_responses=True)

async def get_redis_client():
    return redis_client