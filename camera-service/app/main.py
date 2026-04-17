from fastapi import FastAPI
from app.core.cors import configure_cors
from app.api.camera_routes import router as camera_router
from app.api.capture_routes import router as capture_router
from app.db.connection import connect_db, close_db
from app.events.event_bus import event_bus

app = FastAPI(title="Camera Service", version="1.0")

configure_cors(app)

@app.on_event("startup")
async def startup_event():
    await connect_db()
    await event_bus.connect()

@app.on_event("shutdown")
async def shutdown_event():
    await event_bus.disconnect()
    await close_db()

app.include_router(camera_router, prefix="/api/camera", tags=["camera"])
app.include_router(capture_router, prefix="/api/capture", tags=["capture"])