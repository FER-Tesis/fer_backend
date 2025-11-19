from fastapi import FastAPI
from app.api.emotion_routes import router as emotion_router
from app.db.connection import connect_db, close_db

app = FastAPI(title="Central Service", version="1.0")

@app.on_event("startup")
async def startup_event():
    await connect_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

app.include_router(emotion_router, prefix="/api/emotion", tags=["emotion"])