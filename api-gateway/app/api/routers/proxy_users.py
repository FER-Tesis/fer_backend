from fastapi import APIRouter, Request
import httpx
from app.core.config import settings

router = APIRouter()

@router.get("/users")
async def list_users(request: Request):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.USER_SERVICE_URL}/api/health")
        return {"users_service_health": resp.json()}
