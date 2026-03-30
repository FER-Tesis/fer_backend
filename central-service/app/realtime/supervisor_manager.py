from collections import defaultdict
from copy import deepcopy
from fastapi import WebSocket


class SupervisorManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)
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
        if supervisor_id not in self.supervisor_agents:
            return

        agent_ids = list(self.supervisor_agents[supervisor_id].keys())

        for agent_id in agent_ids:
            if agent_id in self.agent_to_supervisors:
                self.agent_to_supervisors[agent_id].discard(supervisor_id)
                if not self.agent_to_supervisors[agent_id]:
                    del self.agent_to_supervisors[agent_id]

        del self.supervisor_agents[supervisor_id]

    def load_initial_snapshot(self, supervisor_id: str, agents):
        self._clear_supervisor_cache(supervisor_id)

        for agent in agents:
            agent_id = str(agent.id)

            emotion_value = agent.emotion.value if hasattr(agent.emotion, "value") else agent.emotion

            self.supervisor_agents[supervisor_id][agent_id] = {
                "id": agent_id,
                "name": agent.name,
                "email": agent.email,
                "emotion": emotion_value,
                "timestamp": agent.timestamp.isoformat() if agent.timestamp else None,
            }

            self.agent_to_supervisors[agent_id].add(supervisor_id)

    def apply_relation_assigned(self, supervisor_id: str, agent: dict):
        if supervisor_id not in self.supervisor_agents:
            return

        agent_id = str(agent["id"])

        self.supervisor_agents[supervisor_id][agent_id] = {
            "id": agent_id,
            "name": agent["name"],
            "email": agent.get("email"),
            "emotion": agent.get("emotion"),
            "timestamp": agent.get("timestamp"),
        }

        self.agent_to_supervisors[agent_id].add(supervisor_id)

    def apply_relation_removed(self, supervisor_id: str, agent_id: str):
        agent_id = str(agent_id)

        if supervisor_id in self.supervisor_agents:
            self.supervisor_agents[supervisor_id].pop(agent_id, None)

        if agent_id in self.agent_to_supervisors:
            self.agent_to_supervisors[agent_id].discard(supervisor_id)
            if not self.agent_to_supervisors[agent_id]:
                del self.agent_to_supervisors[agent_id]

    def apply_agent_emotion_update(self, agent_id: str, emotion: str | None, timestamp: str | None):
        agent_id = str(agent_id)
        supervisor_ids = list(self.agent_to_supervisors.get(agent_id, set()))

        emotion_value = emotion.value if hasattr(emotion, "value") else emotion

        for supervisor_id in supervisor_ids:
            if supervisor_id in self.supervisor_agents and agent_id in self.supervisor_agents[supervisor_id]:
                self.supervisor_agents[supervisor_id][agent_id]["emotion"] = emotion_value
                self.supervisor_agents[supervisor_id][agent_id]["timestamp"] = timestamp

        return supervisor_ids

    def build_snapshot_payload(self, supervisor_id: str) -> dict:
        agents = list(self.supervisor_agents.get(supervisor_id, {}).values())

        return {
            "type": "supervisor-agents-snapshot",
            "agents": deepcopy(agents)
        }

    async def broadcast_snapshot(self, supervisor_id: str):
        payload = self.build_snapshot_payload(supervisor_id)
        sockets = list(self.connections.get(supervisor_id, set()))
        dead = []

        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception as e:
                dead.append(ws)

        for ws in dead:
            self.unregister(supervisor_id, ws)


supervisor_manager = SupervisorManager()