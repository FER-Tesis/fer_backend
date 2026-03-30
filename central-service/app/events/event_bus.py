import json
from redis.asyncio import Redis
from app.core.config import settings


class EventBus:
    def __init__(self):
        self.redis: Redis | None = None

    async def connect(self):
        if self.redis is None:
            self.redis = Redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )

    async def disconnect(self):
        if self.redis is not None:
            await self.redis.aclose()
            self.redis = None

    async def publish(self, channel: str, payload: dict):
        if self.redis is None:
            await self.connect()

        await self.redis.publish(channel, json.dumps(payload))


event_bus = EventBus()