from collections import defaultdict
from copy import deepcopy
from fastapi import WebSocket


class SupervisorCameraManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)
        self.supervisor_cameras: dict[str, dict[str, dict]] = defaultdict(dict)
        self.agent_to_supervisors: dict[str, set[str]] = defaultdict(set)
        self.camera_to_agent: dict[str, str] = {}

    async def register(self, supervisor_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[supervisor_id].add(websocket)

    def unregister(self, supervisor_id: str, websocket: WebSocket):
        if supervisor_id in self.connections:
            self.connections[supervisor_id].discard(websocket)

            if not self.connections[supervisor_id]:
                del self.connections[supervisor_id]
                self._clear_supervisor_cache(supervisor_id)

    def has_supervisor(self, supervisor_id: str) -> bool:
        return supervisor_id in self.connections

    def _clear_supervisor_cache(self, supervisor_id: str):
        if supervisor_id not in self.supervisor_cameras:
            return

        agent_ids = list(self.supervisor_cameras[supervisor_id].keys())

        for agent_id in agent_ids:
            row = self.supervisor_cameras[supervisor_id].get(agent_id, {})
            camera_id = row.get("camera_id")

            if agent_id in self.agent_to_supervisors:
                self.agent_to_supervisors[agent_id].discard(supervisor_id)
                if not self.agent_to_supervisors[agent_id]:
                    del self.agent_to_supervisors[agent_id]

            if camera_id and self.camera_to_agent.get(str(camera_id)) == agent_id:
                del self.camera_to_agent[str(camera_id)]

        del self.supervisor_cameras[supervisor_id]

    def load_initial_snapshot(self, supervisor_id: str, rows):
        self._clear_supervisor_cache(supervisor_id)

        for row in rows:
            row_data = row.model_dump() if hasattr(row, "model_dump") else dict(row)
            agent_id = str(row_data["agent_id"])
            camera_id = row_data.get("camera_id")

            self.supervisor_cameras[supervisor_id][agent_id] = row_data
            self.agent_to_supervisors[agent_id].add(supervisor_id)

            if camera_id:
                self.camera_to_agent[str(camera_id)] = agent_id

    def upsert_row(self, supervisor_id: str, row: dict):
        if supervisor_id not in self.supervisor_cameras:
            return

        agent_id = str(row["agent_id"])
        camera_id = row.get("camera_id")

        previous = self.supervisor_cameras[supervisor_id].get(agent_id)
        if previous and previous.get("camera_id") and previous.get("camera_id") != camera_id:
            old_camera_id = str(previous["camera_id"])
            if self.camera_to_agent.get(old_camera_id) == agent_id:
                del self.camera_to_agent[old_camera_id]

        self.supervisor_cameras[supervisor_id][agent_id] = row
        self.agent_to_supervisors[agent_id].add(supervisor_id)

        if camera_id:
            self.camera_to_agent[str(camera_id)] = agent_id

    def apply_relation_removed(self, supervisor_id: str, agent_id: str):
        agent_id = str(agent_id)

        if supervisor_id in self.supervisor_cameras:
            previous = self.supervisor_cameras[supervisor_id].pop(agent_id, None)

            if previous and previous.get("camera_id"):
                camera_id = str(previous["camera_id"])
                if self.camera_to_agent.get(camera_id) == agent_id:
                    del self.camera_to_agent[camera_id]

        if agent_id in self.agent_to_supervisors:
            self.agent_to_supervisors[agent_id].discard(supervisor_id)
            if not self.agent_to_supervisors[agent_id]:
                del self.agent_to_supervisors[agent_id]

    def get_supervisors_by_agent(self, agent_id: str) -> list[str]:
        return list(self.agent_to_supervisors.get(str(agent_id), set()))

    def get_agent_id_by_camera(self, camera_id: str) -> str | None:
        return self.camera_to_agent.get(str(camera_id))

    def build_snapshot_payload(self, supervisor_id: str) -> dict:
        cameras = list(self.supervisor_cameras.get(supervisor_id, {}).values())
        cameras_copy = deepcopy(cameras)
    
        for row in cameras_copy:
            if row.get("last_connection"):
                row["last_connection"] = row["last_connection"].isoformat()
    
        return {
            "type": "supervisor-cameras-snapshot",
            "cameras": cameras_copy
        }

    async def broadcast_snapshot(self, supervisor_id: str):
        payload = self.build_snapshot_payload(supervisor_id)
        sockets = list(self.connections.get(supervisor_id, set()))
        dead = []

        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.unregister(supervisor_id, ws)


supervisor_camera_manager = SupervisorCameraManager()