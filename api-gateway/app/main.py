from fastapi import FastAPI
from app.api.health_routes import router as health_router
from app.api.routers.proxy_users import router as users_router

app = FastAPI()

app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])