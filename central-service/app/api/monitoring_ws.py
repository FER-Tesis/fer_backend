from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio

from app.services import monitoring_service

router = APIRouter()


@router.websocket("/agent/{agent_id}/current")
async def websocket_agent_emotion(websocket: WebSocket, agent_id: str):
    await websocket.accept()

    last_emotion = None

    try:
        while True:
            current = await monitoring_service.get_agent_current(agent_id)

            if current.emotion != last_emotion:
                await websocket.send_json({
                    "emotion": current.emotion,
                    "timestamp": current.timestamp.isoformat()
                })
                last_emotion = current.emotion

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        print(f"WebSocket desconectado para agente {agent_id}.")

    except asyncio.CancelledError:
        print(f"WebSocket cancelado por apagado del servidor (agente: {agent_id}).")

    except Exception as e:
        print(f"Error WebSocket: {e}")

    finally:
        try:
            await websocket.close()
        except:
            pass

@router.websocket("/supervisor/{supervisor_id}/agents")
async def websocket_supervisor_agents(websocket: WebSocket, supervisor_id: str):
    await websocket.accept()

    initial_agents = await monitoring_service.get_supervisor_agents_with_status(supervisor_id)
    last_agents = { a.id: (a.emotion, a.timestamp) for a in initial_agents }

    try:
        while True:
            agents = await monitoring_service.get_supervisor_agents_with_status(supervisor_id)
            
            current_ids = set(a.id for a in agents)
            previous_ids = set(last_agents.keys())

            removed = previous_ids - current_ids
            for agent_id in removed:
                await websocket.send_json({
                    "type": "agent-removed",
                    "agentId": agent_id
                })
                del last_agents[agent_id]

            for agent in agents:
                state = (agent.emotion, agent.timestamp)

                if agent.id not in last_agents:
                    last_agents[agent.id] = state
                    await websocket.send_json({
                        "type": "agent-added",
                        "agentId": agent.id,
                        "name": agent.name,
                        "email": agent.email,
                        "emotion": agent.emotion,
                        "timestamp": agent.timestamp.isoformat() if agent.timestamp else None
                    })
                    continue

                if last_agents[agent.id] != state:
                    last_agents[agent.id] = state
                    await websocket.send_json({
                        "type": "agent-emotion-update",
                        "agentId": agent.id,
                        "name": agent.name,
                        "email": agent.email,
                        "emotion": agent.emotion,
                        "timestamp": agent.timestamp.isoformat() if agent.timestamp else None
                    })

            await asyncio.sleep(1)

    except WebSocketDisconnect:
        print(f"Supervisor WS desconectado: {supervisor_id}")
    except Exception as e:
        print(f"Error en WS supervisor: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass
