from collections import defaultdict
from fastapi import WebSocket


class AgentEmotionManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, agent_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections[agent_id].add(websocket)

    def disconnect(self, agent_id: str, websocket: WebSocket):
        if agent_id in self.connections:
            self.connections[agent_id].discard(websocket)
            if not self.connections[agent_id]:
                del self.connections[agent_id]

    async def broadcast(self, agent_id: str, payload: dict):
        sockets = list(self.connections.get(agent_id, set()))
        dead_sockets = []

        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                dead_sockets.append(ws)

        for ws in dead_sockets:
            self.disconnect(agent_id, ws)


agent_emotion_manager = AgentEmotionManager()