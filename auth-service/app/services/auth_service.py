import httpx
from datetime import timedelta
from app.core.config import settings
from app.core.security import create_access_token, verify_password, decode_token

class AuthError(Exception):
    """Errores de autenticación o registro."""
    pass

async def register_user(data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.USER_SERVICE_URL}/users",
            json=data
        )

        if response.status_code != 201:
            raise AuthError("Failed to register user")

        user = response.json()

        token = create_access_token(
            {"sub": str(user["_id"]), "role": user.get("role")},
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {"access_token": token, "token_type": "bearer"}

async def authenticate_user(email: str, password: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.USER_SERVICE_URL}/find",
            json={"email": email}
        )

        if response.status_code != 200:
            raise AuthError("Invalid credentials")

        user = response.json()

        if not user.get("is_active", True):
            raise AuthError("Inactive account")

        hashed_password = user.get("password")
        if not hashed_password or not verify_password(password, hashed_password):
            raise AuthError("Invalid credentials")

        token = create_access_token(
            {"sub": str(user["_id"]), "role": user.get("role")},
            timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        return {"access_token": token, "token_type": "bearer"}

def verify_token(token: str):
    payload = decode_token(token)
    return {
        "valid": True,
        "user_id": payload.get("sub"),
        "role": payload.get("role"),
        "exp": payload.get("exp")
    }
