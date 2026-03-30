import asyncio
import json
from redis.asyncio import Redis
from app.core.config import settings
from app.realtime.agent_emotion_manager import agent_emotion_manager


class AgentEmotionListener:
    def __init__(self):
        self.redis: Redis | None = None
        self.pubsub = None
        self.task: asyncio.Task | None = None
        self.running = False

    async def start(self):
        if self.running:
            return

        self.redis = Redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe("agent-emotion-updated")

        self.running = True
        self.task = asyncio.create_task(self._consume())

    async def _consume(self):
        try:
            async for message in self.pubsub.listen():
                if not self.running:
                    break

                if message["type"] != "message":
                    continue

                raw_data = message.get("data")
                if not isinstance(raw_data, str):
                    continue

                payload = json.loads(raw_data)

                agent_id = payload.get("agent_id")
                emotion = payload.get("emotion")
                timestamp = payload.get("timestamp")

                if not agent_id:
                    continue

                await agent_emotion_manager.broadcast(
                    agent_id,
                    {
                        "emotion": emotion,
                        "timestamp": timestamp,
                    },
                )
        except asyncio.CancelledError:
            pass

    async def stop(self):
        self.running = False

        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

        if self.pubsub:
            await self.pubsub.aclose()
            self.pubsub = None

        if self.redis:
            await self.redis.aclose()
            self.redis = None


agent_emotion_listener = AgentEmotionListener()