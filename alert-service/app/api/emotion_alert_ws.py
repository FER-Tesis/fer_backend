from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.emotion_alert_manager import emotion_alert_manager
from app.services import emotion_alert_service

router = APIRouter()


@router.websocket("/supervisor/{supervisor_id}/pending")
async def websocket_supervisor_pending_emotion_alerts(
    websocket: WebSocket,
    supervisor_id: str,
):
    await emotion_alert_manager.register(supervisor_id, websocket)

    try:
        agents = await emotion_alert_service.get_supervisor_agents(supervisor_id)
        initial_alerts = await emotion_alert_service.list_pending_emotion_alerts_for_supervisor(
            supervisor_id
        )

        emotion_alert_manager.load_initial_pending_alerts(
            supervisor_id=supervisor_id,
            agents=agents,
            alerts=initial_alerts,
        )

        await emotion_alert_manager.broadcast_pending_alerts(supervisor_id)

        while True:
            await websocket.receive()

    except WebSocketDisconnect:
        print(f"Supervisor emotion alerts WS desconectado: {supervisor_id}")

    except Exception as e:
        print(f"Error en WS emotion alerts supervisor {supervisor_id}: {e}")

    finally:
        emotion_alert_manager.unregister(supervisor_id, websocket)