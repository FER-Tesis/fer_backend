from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.camera_alert_manager import camera_alert_manager
import app.services.camera_alert_service as camera_alert_service

router = APIRouter()


@router.websocket("/supervisor/{supervisor_id}/active")
async def websocket_supervisor_active_camera_alerts(
    websocket: WebSocket,
    supervisor_id: str,
):
    await camera_alert_manager.register(supervisor_id, websocket)

    try:
        agent_ids = await camera_alert_service.get_supervisor_agent_ids(supervisor_id)
        initial_alerts = await camera_alert_service.list_active_camera_alerts_for_supervisor(
            supervisor_id
        )

        camera_alert_manager.load_initial_active_alerts(
            supervisor_id=supervisor_id,
            agent_ids=agent_ids,
            alerts=initial_alerts,
        )

        await camera_alert_manager.broadcast_active_alerts(supervisor_id)

        while True:
            await websocket.receive()

    except WebSocketDisconnect:
        print(f"Supervisor camera alerts WS desconectado: {supervisor_id}")

    except Exception as e:
        print(f"Error en WS camera alerts supervisor {supervisor_id}: {e}")

    finally:
        camera_alert_manager.unregister(supervisor_id, websocket)