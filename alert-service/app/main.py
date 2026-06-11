from fastapi import FastAPI
from app.core.cors import configure_cors
from app.api.camera_alert_routes import router as camera_alert_router
from app.api.camera_alert_ws import router as camera_alert_ws_router
from app.api.emotion_alert_routes import router as emotion_alert_router
from app.db.connection import connect_db, close_db
from app.events.event_bus import event_bus
from app.events.alert_event_bus import alert_event_bus
from app.realtime.camera_alert_listener import camera_alert_listener
from app.realtime.emotion_alert_listener import emotion_alert_listener

app = FastAPI(title="Alert Service", version="1.0", root_path="/alerts")

configure_cors(app)

@app.on_event("startup")
async def startup_event():
    await connect_db()
    await event_bus.connect()
    await alert_event_bus.connect()
    await camera_alert_listener.start()
    await emotion_alert_listener.start()

@app.on_event("shutdown")
async def shutdown_event():
    await camera_alert_listener.stop()
    await emotion_alert_listener.stop()
    await event_bus.disconnect()
    await alert_event_bus.disconnect()
    await close_db()

app.include_router(camera_alert_router, prefix="/api/camera/alert", tags=["camera_alert"])
app.include_router(camera_alert_ws_router, prefix="/api/camera/alert/ws", tags=["camera_alerts_ws"])
app.include_router(emotion_alert_router, prefix="/api/emotion/alert", tags=["emotion_alert"])