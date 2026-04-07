import asyncio
import json
from redis.asyncio import Redis

from app.core.config import settings
from app.realtime.camera_alert_manager import camera_alert_manager
from app.services import camera_alert_service


class CameraAlertListener:
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
            "camera-alert-created",
            "camera-alert-resolved",
            "camera-alert-deleted",
            "camera-assignment-changed",
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

                if channel == "camera-alert-created":
                    await self._handle_camera_alert_created(payload)

                elif channel == "camera-alert-resolved":
                    await self._handle_camera_alert_resolved(payload)

                elif channel == "camera-alert-deleted":
                    await self._handle_camera_alert_deleted(payload)

                elif channel == "camera-assignment-changed":
                    await self._handle_camera_assignment_changed(payload)

                elif channel == "relation-assigned":
                    await self._handle_relation_assigned(payload)

                elif channel == "relation-removed":
                    await self._handle_relation_removed(payload)

        except asyncio.CancelledError:
            pass

    async def _handle_camera_alert_created(self, payload: dict):
        supervisor_ids = camera_alert_manager.apply_alert_created(payload)

        for supervisor_id in supervisor_ids:
            await camera_alert_manager.broadcast_active_alerts(supervisor_id)

    async def _handle_camera_alert_resolved(self, payload: dict):
        alert_id = str(payload["alert_id"])
        agent_id = str(payload["agent_id"])

        supervisor_ids = camera_alert_manager.apply_alert_resolved(
            alert_id=alert_id,
            agent_id=agent_id,
        )

        for supervisor_id in supervisor_ids:
            await camera_alert_manager.broadcast_active_alerts(supervisor_id)

    async def _handle_camera_alert_deleted(self, payload: dict):
        alert_id = str(payload["alert_id"])
        agent_id = str(payload["agent_id"])

        supervisor_ids = camera_alert_manager.apply_alert_deleted(
            alert_id=alert_id,
            agent_id=agent_id,
        )

        for supervisor_id in supervisor_ids:
            await camera_alert_manager.broadcast_active_alerts(supervisor_id)

    async def _handle_camera_assignment_changed(self, payload: dict):
        camera_id = str(payload["camera_id"])
        await camera_alert_service.recreate_active_alert_for_camera_assignment_change(
            camera_id
        )

    async def _handle_relation_assigned(self, payload: dict):
        supervisor_id = str(payload["supervisor_id"])

        if not camera_alert_manager.has_supervisor(supervisor_id):
            return

        agent = payload["agent"]
        agent_id = str(agent["id"])

        active_alerts = await camera_alert_service.list_active_camera_alerts_for_agent(
            agent_id
        )

        camera_alert_manager.apply_relation_assigned(
            supervisor_id=supervisor_id,
            agent_id=agent_id,
            active_alerts=active_alerts,
        )
        await camera_alert_manager.broadcast_active_alerts(supervisor_id)

    async def _handle_relation_removed(self, payload: dict):
        supervisor_id = str(payload["supervisor_id"])

        if not camera_alert_manager.has_supervisor(supervisor_id):
            return

        agent_id = str(payload["agent_id"])
        camera_alert_manager.apply_relation_removed(supervisor_id, agent_id)
        await camera_alert_manager.broadcast_active_alerts(supervisor_id)

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


camera_alert_listener = CameraAlertListener()