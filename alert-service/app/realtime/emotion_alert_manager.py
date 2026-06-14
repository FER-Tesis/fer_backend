from collections import defaultdict
from copy import deepcopy
from fastapi import WebSocket


ALERT_TYPE_LABELS = {
    "negative_count": "Alta frecuencia de emociones negativas",
    "continuous_emotion": "Emoción negativa sostenida",
}

SEVERITY_LABELS = {
    "low": "Baja",
    "medium": "Media",
    "high": "Alta",
}


class EmotionAlertManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)
        self.supervisor_pending_alerts: dict[str, dict[str, dict]] = defaultdict(dict)
        self.supervisor_agents: dict[str, dict[str, dict]] = defaultdict(dict)
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
            for agent_id in list(self.supervisor_agents[supervisor_id].keys()):
                if agent_id in self.agent_to_supervisors:
                    self.agent_to_supervisors[agent_id].discard(supervisor_id)
                    if not self.agent_to_supervisors[agent_id]:
                        del self.agent_to_supervisors[agent_id]

            del self.supervisor_agents[supervisor_id]

        if supervisor_id in self.supervisor_pending_alerts:
            del self.supervisor_pending_alerts[supervisor_id]

    def load_initial_pending_alerts(
        self,
        supervisor_id: str,
        agents: list[dict],
        alerts: list[dict],
    ):
        self._clear_supervisor_cache(supervisor_id)

        for agent in agents:
            agent_id = str(agent["id"])

            self.supervisor_agents[supervisor_id][agent_id] = {
                "id": agent_id,
                "name": agent.get("name", ""),
                "email": agent.get("email", ""),
            }

            self.agent_to_supervisors[agent_id].add(supervisor_id)

        for alert in alerts:
            alert_id = str(alert["_id"])
            self.supervisor_pending_alerts[supervisor_id][alert_id] = self._normalize_alert(
                supervisor_id,
                alert,
            )

    def apply_alert_created(self, alert: dict) -> list[str]:
        agent_id = str(alert["agent_id"])
        supervisor_ids = list(self.agent_to_supervisors.get(agent_id, set()))

        for supervisor_id in supervisor_ids:
            alert_id = str(alert["_id"])
            self.supervisor_pending_alerts[supervisor_id][alert_id] = self._normalize_alert(
                supervisor_id,
                alert,
            )

        return supervisor_ids

    def apply_alert_acknowledged(self, alert_id: str, agent_id: str) -> list[str]:
        alert_id = str(alert_id)
        agent_id = str(agent_id)

        supervisor_ids = list(self.agent_to_supervisors.get(agent_id, set()))

        for supervisor_id in supervisor_ids:
            if supervisor_id in self.supervisor_pending_alerts:
                self.supervisor_pending_alerts[supervisor_id].pop(alert_id, None)

        return supervisor_ids

    def apply_relation_assigned(
        self,
        supervisor_id: str,
        agent: dict,
        pending_alerts: list[dict],
    ):
        if supervisor_id not in self.connections:
            return

        agent_id = str(agent["id"])

        self.supervisor_agents[supervisor_id][agent_id] = {
            "id": agent_id,
            "name": agent.get("name", ""),
            "email": agent.get("email", ""),
        }

        self.agent_to_supervisors[agent_id].add(supervisor_id)

        for alert in pending_alerts:
            alert_id = str(alert["_id"])
            self.supervisor_pending_alerts[supervisor_id][alert_id] = self._normalize_alert(
                supervisor_id,
                alert,
            )

    def apply_relation_removed(self, supervisor_id: str, agent_id: str):
        agent_id = str(agent_id)

        if supervisor_id in self.supervisor_agents:
            self.supervisor_agents[supervisor_id].pop(agent_id, None)

        if agent_id in self.agent_to_supervisors:
            self.agent_to_supervisors[agent_id].discard(supervisor_id)
            if not self.agent_to_supervisors[agent_id]:
                del self.agent_to_supervisors[agent_id]

        if supervisor_id in self.supervisor_pending_alerts:
            alerts = self.supervisor_pending_alerts[supervisor_id]

            to_remove = [
                alert_id
                for alert_id, alert in alerts.items()
                if str(alert["agent_id"]) == agent_id
            ]

            for alert_id in to_remove:
                alerts.pop(alert_id, None)

    def build_pending_alerts_payload(self, supervisor_id: str) -> dict:
        alerts = list(self.supervisor_pending_alerts.get(supervisor_id, {}).values())
        alerts.sort(key=lambda item: item["created_at"], reverse=True)

        return {
            "type": "supervisor-emotion-pending-alerts-snapshot",
            "alerts": deepcopy(alerts),
        }

    async def broadcast_pending_alerts(self, supervisor_id: str):
        payload = self.build_pending_alerts_payload(supervisor_id)
        sockets = list(self.connections.get(supervisor_id, set()))
        dead = []

        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.unregister(supervisor_id, ws)

    def _normalize_alert(self, supervisor_id: str, alert: dict) -> dict:
        created_at = alert.get("created_at")
        updated_at = alert.get("updated_at")

        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()

        if hasattr(updated_at, "isoformat"):
            updated_at = updated_at.isoformat()

        rule_type = alert.get("rule_type", "")
        severity = alert.get("severity", "")
        agent_id = str(alert["agent_id"])

        agent = self.supervisor_agents.get(supervisor_id, {}).get(agent_id, {})

        return {
            "_id": str(alert["_id"]),
            "agent_id": agent_id,
            "agent_name": agent.get("name", ""),
            "agent_email": agent.get("email", ""),
            "rule_type": rule_type,
            "alert_type": ALERT_TYPE_LABELS.get(rule_type, rule_type),
            "severity": severity,
            "severity_label": SEVERITY_LABELS.get(severity, severity),
            "status": alert["status"],
            "created_at": created_at,
            "updated_at": updated_at,
        }


emotion_alert_manager = EmotionAlertManager()