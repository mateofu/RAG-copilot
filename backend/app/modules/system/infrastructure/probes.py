from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class DatabaseProbe:
    name = "database"

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def is_ready(self) -> bool:
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True


class RedisProbe:
    name = "redis"

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url

    async def is_ready(self) -> bool:
        client = Redis.from_url(self._redis_url)
        try:
            return bool(await client.ping())
        finally:
            await client.aclose()
