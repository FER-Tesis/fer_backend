import asyncio
import json
from redis.asyncio import Redis
from app.core.config import settings
from app.realtime.supervisor_manager import supervisor_manager
from app.services import monitoring_service


class SupervisorListener:
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
        await self.pubsub.subscribe(
            "relation-assigned",
            "relation-removed",
            "agent-emotion-updated",
        )

        self.running = True
        self.task = asyncio.create_task(self._consume())

    async def _consume(self):
        try:
            async for message in self.pubsub.listen():
                if not self.running:
                    break

                if message["type"] != "message":
                    continue

                channel = message.get("channel")
                raw_data = message.get("data")

                if not isinstance(raw_data, str):
                    continue

                payload = json.loads(raw_data)

                if channel == "relation-assigned":
                    await self._handle_relation_assigned(payload)

                elif channel == "relation-removed":
                    await self._handle_relation_removed(payload)

                elif channel == "agent-emotion-updated":
                    await self._handle_emotion_update(payload)

        except asyncio.CancelledError:
            pass

    async def _handle_relation_assigned(self, payload: dict):
        supervisor_id = str(payload["supervisor_id"])

        if not supervisor_manager.has_supervisor(supervisor_id):
            return

        agent = payload["agent"]
        agent_id = str(agent["id"])

        current = await monitoring_service.get_agent_current(agent_id)

        enriched_agent = {
            "id": agent_id,
            "name": agent["name"],
            "email": agent["email"],
            "emotion": current.emotion,
            "timestamp": current.timestamp.isoformat() if current.timestamp else None,
        }

        supervisor_manager.apply_relation_assigned(supervisor_id, enriched_agent)
        await supervisor_manager.broadcast_snapshot(supervisor_id)

    async def _handle_relation_removed(self, payload: dict):
        supervisor_id = str(payload["supervisor_id"])

        if not supervisor_manager.has_supervisor(supervisor_id):
            return

        agent_id = str(payload["agent_id"])
        supervisor_manager.apply_relation_removed(supervisor_id, agent_id)
        await supervisor_manager.broadcast_snapshot(supervisor_id)

    async def _handle_emotion_update(self, payload: dict):
        agent_id = str(payload["agent_id"])
        emotion = payload.get("emotion")
        timestamp = payload.get("timestamp")

        supervisor_ids = supervisor_manager.apply_agent_emotion_update(
            agent_id=agent_id,
            emotion=emotion,
            timestamp=timestamp,
        )

        for supervisor_id in supervisor_ids:
            await supervisor_manager.broadcast_snapshot(supervisor_id)

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


supervisor_listener = SupervisorListener()