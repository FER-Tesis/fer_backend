from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.realtime.agent_emotion_manager import agent_emotion_manager
from app.realtime.supervisor_manager import supervisor_manager
import app.services.monitoring_service as monitoring_service

router = APIRouter()

@router.websocket("/agent/{agent_id}/current")
async def websocket_agent_emotion(websocket: WebSocket, agent_id: str):
    await agent_emotion_manager.connect(agent_id, websocket)

    try:
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        print(f"WebSocket desconectado para agente {agent_id}.")
    except Exception as e:
        print(f"Error WebSocket agente {agent_id}: {e}")
    finally:
        agent_emotion_manager.disconnect(agent_id, websocket)

@router.websocket("/supervisor/{supervisor_id}/agents")
async def websocket_supervisor_agents(websocket: WebSocket, supervisor_id: str):
    await supervisor_manager.register(supervisor_id, websocket)

    try:
        initial_agents = await monitoring_service.get_supervisor_agents_with_status(supervisor_id)
        supervisor_manager.load_initial_snapshot(supervisor_id, initial_agents)
        await supervisor_manager.broadcast_snapshot(supervisor_id)

        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        print(f"Supervisor WS desconectado: {supervisor_id}")
    except Exception as e:
        print(f"Error en WS supervisor: {e}")
    finally:
        supervisor_manager.unregister(supervisor_id, websocket)