import json
from redis.asyncio import Redis
from app.core.config import settings


class AlertEventPublisher:
    def __init__(self):
        self.redis: Redis | None = None

    async def connect(self):
        if self.redis is None:
            self.redis = Redis.from_url(
                settings.REDIS_URL,
                db=1,  # DB 1 para eventos emocionales
                encoding="utf-8",
                decode_responses=True,
            )

    async def disconnect(self):
        if self.redis is not None:
            await self.redis.aclose()
            self.redis = None

    async def publish_emotion_alert_event(self, agent_id: str, emotion: str, timestamp: str):
        if self.redis is None:
            await self.connect()

        await self.redis.publish(
            "emotion-alert-evaluation",
            json.dumps({
                "agent_id": agent_id,
                "emotion": emotion,
                "timestamp": timestamp,
            })
        )


alert_event_publisher = AlertEventPublisher()
