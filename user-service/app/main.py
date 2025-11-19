from fastapi import FastAPI
from app.api.health_routes import router as health_router
from app.api.users_routes import router as user_router
from app.db.connection import connect_db, close_db

app = FastAPI(title="User Service", version="1.0")

@app.on_event("startup")
async def startup_event():
    await connect_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(user_router, prefix="/api/user", tags=["user"])