from collections import defaultdict
from copy import deepcopy
from fastapi import WebSocket


class CameraAlertManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)
        self.supervisor_active_alerts: dict[str, dict[str, dict]] = defaultdict(dict)
        self.supervisor_agents: dict[str, set[str]] = defaultdict(set)
        self.agent_to_supervisors: dict[str, set[str]] = defaultdict(set)

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
        if supervisor_id in self.supervisor_agents:
            for agent_id in list(self.supervisor_agents[supervisor_id]):
                if agent_id in self.agent_to_supervisors:
                    self.agent_to_supervisors[agent_id].discard(supervisor_id)
                    if not self.agent_to_supervisors[agent_id]:
                        del self.agent_to_supervisors[agent_id]

            del self.supervisor_agents[supervisor_id]

        if supervisor_id in self.supervisor_active_alerts:
            del self.supervisor_active_alerts[supervisor_id]

    def load_initial_active_alerts(
        self,
        supervisor_id: str,
        agent_ids: list[str],
        alerts: list[dict],
    ):
        self._clear_supervisor_cache(supervisor_id)

        self.supervisor_agents[supervisor_id] = set(str(agent_id) for agent_id in agent_ids)

        for agent_id in self.supervisor_agents[supervisor_id]:
            self.agent_to_supervisors[agent_id].add(supervisor_id)

        for alert in alerts:
            alert_id = str(alert["_id"])
            self.supervisor_active_alerts[supervisor_id][alert_id] = self._normalize_alert(alert)

    def apply_relation_assigned(
        self,
        supervisor_id: str,
        agent_id: str,
        active_alerts: list[dict],
    ):
        agent_id = str(agent_id)

        if supervisor_id not in self.connections:
            return

        self.supervisor_agents[supervisor_id].add(agent_id)
        self.agent_to_supervisors[agent_id].add(supervisor_id)

        for alert in active_alerts:
            alert_id = str(alert["_id"])
            self.supervisor_active_alerts[supervisor_id][alert_id] = self._normalize_alert(alert)

    def apply_relation_removed(self, supervisor_id: str, agent_id: str):
        agent_id = str(agent_id)

        if supervisor_id in self.supervisor_agents:
            self.supervisor_agents[supervisor_id].discard(agent_id)

        if agent_id in self.agent_to_supervisors:
            self.agent_to_supervisors[agent_id].discard(supervisor_id)
            if not self.agent_to_supervisors[agent_id]:
                del self.agent_to_supervisors[agent_id]

        if supervisor_id in self.supervisor_active_alerts:
            alerts = self.supervisor_active_alerts[supervisor_id]
            to_remove = [
                alert_id
                for alert_id, alert in alerts.items()
                if str(alert["agent_id"]) == agent_id
            ]

            for alert_id in to_remove:
                alerts.pop(alert_id, None)

    def apply_alert_created(self, alert: dict) -> list[str]:
        normalized = self._normalize_alert(alert)
        agent_id = str(normalized["agent_id"])
        alert_id = str(normalized["_id"])

        supervisor_ids = list(self.agent_to_supervisors.get(agent_id, set()))

        for supervisor_id in supervisor_ids:
            self.supervisor_active_alerts[supervisor_id][alert_id] = normalized

        return supervisor_ids

    def apply_alert_resolved(self, alert_id: str, agent_id: str) -> list[str]:
        alert_id = str(alert_id)
        agent_id = str(agent_id)

        supervisor_ids = list(self.agent_to_supervisors.get(agent_id, set()))

        for supervisor_id in supervisor_ids:
            if supervisor_id in self.supervisor_active_alerts:
                self.supervisor_active_alerts[supervisor_id].pop(alert_id, None)

        return supervisor_ids

    def apply_alert_deleted(self, alert_id: str, agent_id: str) -> list[str]:
        return self.apply_alert_resolved(alert_id=alert_id, agent_id=agent_id)

    def build_active_alerts_payload(self, supervisor_id: str) -> dict:
        alerts = list(self.supervisor_active_alerts.get(supervisor_id, {}).values())
        alerts.sort(key=lambda item: item["created_at"], reverse=True)

        return {
            "type": "supervisor-camera-active-alerts-snapshot",
            "alerts": deepcopy(alerts),
        }

    async def broadcast_active_alerts(self, supervisor_id: str):
        payload = self.build_active_alerts_payload(supervisor_id)
        sockets = list(self.connections.get(supervisor_id, set()))
        dead = []

        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.unregister(supervisor_id, ws)

    def _normalize_alert(self, alert: dict) -> dict:
        created_at = alert.get("created_at")

        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()

        return {
            "_id": str(alert["_id"]),
            "camera_id": str(alert["camera_id"]),
            "agent_id": str(alert["agent_id"]),
            "description": alert["description"],
            "status": alert["status"],
            "created_at": created_at,
        }


camera_alert_manager = CameraAlertManager()