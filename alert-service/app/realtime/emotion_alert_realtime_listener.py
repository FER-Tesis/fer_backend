import asyncio
import json
from redis.asyncio import Redis

from app.core.config import settings
from app.realtime.emotion_alert_manager import emotion_alert_manager
from app.services import emotion_alert_service


class EmotionAlertRealtimeListener:
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
            db=1,
            encoding="utf-8",
            decode_responses=True,
        )

        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(
            "emotion-alert-created",
            "emotion-alert-acknowledged",
            "relation-assigned",
            "relation-removed",
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

                if channel == "emotion-alert-created":
                    await self._handle_emotion_alert_created(payload)

                elif channel == "emotion-alert-acknowledged":
                    await self._handle_emotion_alert_acknowledged(payload)

                elif channel == "relation-assigned":
                    await self._handle_relation_assigned(payload)

                elif channel == "relation-removed":
                    await self._handle_relation_removed(payload)

        except asyncio.CancelledError:
            pass

    async def _handle_emotion_alert_created(self, payload: dict):
        supervisor_ids = emotion_alert_manager.apply_alert_created(payload)

        for supervisor_id in supervisor_ids:
            await emotion_alert_manager.broadcast_pending_alerts(supervisor_id)

    async def _handle_emotion_alert_acknowledged(self, payload: dict):
        alert_id = str(payload["alert_id"])
        agent_id = str(payload["agent_id"])

        supervisor_ids = emotion_alert_manager.apply_alert_acknowledged(
            alert_id=alert_id,
            agent_id=agent_id,
        )

        for supervisor_id in supervisor_ids:
            await emotion_alert_manager.broadcast_pending_alerts(supervisor_id)

    async def _handle_relation_assigned(self, payload: dict):
        supervisor_id = str(payload["supervisor_id"])

        if not emotion_alert_manager.has_supervisor(supervisor_id):
            return

        agent = payload["agent"]
        agent_id = str(agent["id"])

        pending_alerts = await emotion_alert_service.list_pending_emotion_alerts_for_agent(
            agent_id
        )

        emotion_alert_manager.apply_relation_assigned(
            supervisor_id=supervisor_id,
            agent=agent,
            pending_alerts=pending_alerts,
        )

        await emotion_alert_manager.broadcast_pending_alerts(supervisor_id)

    async def _handle_relation_removed(self, payload: dict):
        supervisor_id = str(payload["supervisor_id"])

        if not emotion_alert_manager.has_supervisor(supervisor_id):
            return

        agent_id = str(payload["agent_id"])

        emotion_alert_manager.apply_relation_removed(
            supervisor_id=supervisor_id,
            agent_id=agent_id,
        )

        await emotion_alert_manager.broadcast_pending_alerts(supervisor_id)

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


emotion_alert_realtime_listener = EmotionAlertRealtimeListener()