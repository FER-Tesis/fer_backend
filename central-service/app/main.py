from fastapi import FastAPI
from app.core.cors import configure_cors
from app.api.emotion_routes import router as emotion_router
from app.api.monitoring_routes import router as monitoring_router
from app.api.monitoring_ws import router as monitoring_ws_router
from app.db.connection import connect_db, close_db
from app.events.event_bus import event_bus
from app.realtime.agent_emotion_listener import agent_emotion_listener
from app.realtime.supervisor_listener import supervisor_listener

app = FastAPI(title="Central Service", version="1.0")

configure_cors(app)

@app.on_event("startup")
async def startup_event():
    await connect_db()
    await event_bus.connect()
    await agent_emotion_listener.start()
    await supervisor_listener.start()

@app.on_event("shutdown")
async def shutdown_event():
    await agent_emotion_listener.stop()
    await supervisor_listener.stop()
    await event_bus.disconnect()
    await close_db()

app.include_router(emotion_router, prefix="/api/emotion", tags=["emotion"])
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["monitoring"])
app.include_router(monitoring_ws_router, prefix="/api/monitoring/ws", tags=["monitoring_ws"])