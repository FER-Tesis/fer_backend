from fastapi import FastAPI
from app.api.camera_routes import router as camera_router
from app.db.connection import connect_db, close_db

app = FastAPI(title="Camera Service", version="1.0")

@app.on_event("startup")
async def startup_event():
    await connect_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

app.include_router(camera_router, prefix="/api/camera", tags=["camera"])