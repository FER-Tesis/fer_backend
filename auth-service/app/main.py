from fastapi import FastAPI
from app.api.auth_routes import router as auth_router

app = FastAPI(title="Auth Service", version="1.0")

app.include_router(auth_router, prefix="/api/user", tags=["auth"])