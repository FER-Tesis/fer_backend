import asyncio
import json
from redis.asyncio import Redis
from app.core.config import settings
from app.realtime.supervisor_camera_manager import supervisor_camera_manager
from app.services import monitoring_service


class SupervisorCameraListener:
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
            "camera-status-updated",
            "camera-assignment-updated",
            "camera-created",
            "camera-deleted",
            "capture-session-started",
            "capture-session-closed",
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
                elif channel == "camera-status-updated":
                    await self._handle_camera_status_updated(payload)
                elif channel == "camera-assignment-updated":
                    await self._handle_camera_assignment_updated(payload)
                elif channel == "camera-created":
                    await self._handle_camera_created(payload)
                elif channel == "camera-deleted":
                    await self._handle_camera_deleted(payload)
                elif channel == "capture-session-started":
                    await self._handle_capture_session_event(payload)
                elif channel == "capture-session-closed":
                    await self._handle_capture_session_event(payload)

        except asyncio.CancelledError:
            pass

    async def _rebuild_and_broadcast(self, supervisor_id: str, agent_id: str):
        if not supervisor_camera_manager.has_supervisor(supervisor_id):
            return

        agents = await monitoring_service._fetch_supervisor_agents(supervisor_id)
        agent = next((a for a in agents if str(a["id"]) == str(agent_id)), None)
        if not agent:
            return

        row = await monitoring_service.build_supervisor_camera_row(agent)
        supervisor_camera_manager.upsert_row(supervisor_id, row.model_dump())
        await supervisor_camera_manager.broadcast_snapshot(supervisor_id)

    async def _handle_relation_assigned(self, payload: dict):
        supervisor_id = str(payload["supervisor_id"])

        if not supervisor_camera_manager.has_supervisor(supervisor_id):
            return

        agent = payload["agent"]
        row = await monitoring_service.build_supervisor_camera_row(agent)
        supervisor_camera_manager.upsert_row(supervisor_id, row.model_dump())
        await supervisor_camera_manager.broadcast_snapshot(supervisor_id)

    async def _handle_relation_removed(self, payload: dict):
        supervisor_id = str(payload["supervisor_id"])

        if not supervisor_camera_manager.has_supervisor(supervisor_id):
            return

        agent_id = str(payload["agent_id"])
        supervisor_camera_manager.apply_relation_removed(supervisor_id, agent_id)
        await supervisor_camera_manager.broadcast_snapshot(supervisor_id)

    async def _handle_camera_status_updated(self, payload: dict):
        agent_id = payload.get("assigned_user_id")
        if not agent_id:
            return

        supervisor_ids = supervisor_camera_manager.get_supervisors_by_agent(agent_id)

        for supervisor_id in supervisor_ids:
            await self._rebuild_and_broadcast(supervisor_id, str(agent_id))

    async def _handle_camera_assignment_updated(self, payload: dict):
        previous_agent_id = payload.get("previous_assigned_user_id")
        new_agent_id = payload.get("new_assigned_user_id")

        if previous_agent_id:
            for supervisor_id in supervisor_camera_manager.get_supervisors_by_agent(previous_agent_id):
                await self._rebuild_and_broadcast(supervisor_id, str(previous_agent_id))

        if new_agent_id:
            for supervisor_id in supervisor_camera_manager.get_supervisors_by_agent(new_agent_id):
                await self._rebuild_and_broadcast(supervisor_id, str(new_agent_id))

    async def _handle_camera_created(self, payload: dict):
        agent_id = payload.get("assigned_user_id")
        if not agent_id:
            return

        for supervisor_id in supervisor_camera_manager.get_supervisors_by_agent(agent_id):
            await self._rebuild_and_broadcast(supervisor_id, str(agent_id))

    async def _handle_camera_deleted(self, payload: dict):
        agent_id = payload.get("assigned_user_id")
        if not agent_id:
            return

        for supervisor_id in supervisor_camera_manager.get_supervisors_by_agent(agent_id):
            await self._rebuild_and_broadcast(supervisor_id, str(agent_id))

    async def _handle_capture_session_event(self, payload: dict):
        camera_id = payload.get("camera_id")
        if not camera_id:
            return

        agent_id = supervisor_camera_manager.get_agent_id_by_camera(camera_id)
        if not agent_id:
            return

        supervisor_ids = supervisor_camera_manager.get_supervisors_by_agent(agent_id)

        for supervisor_id in supervisor_ids:
            await self._rebuild_and_broadcast(supervisor_id, str(agent_id))

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


supervisor_camera_listener = SupervisorCameraListener()