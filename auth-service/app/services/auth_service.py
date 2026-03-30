import httpx
from datetime import timedelta
from app.core.config import settings
from app.core.security import create_access_token, verify_password, decode_token

class AuthError(Exception):
    """Errores de autenticación o registro."""
    pass


async def _handle_agent_capture_on_login(user: dict):
    if user.get("role") != "agent":
        return

    user_id = str(user["_id"])

    async with httpx.AsyncClient() as client:
        camera_response = await client.get(
            f"{settings.CAMERA_SERVICE_URL}/camera/cameras/assigned/user/{user_id}"
        )

        if camera_response.status_code == 404:
            return

        if camera_response.status_code != 200:
            raise AuthError("Failed to get assigned camera")

        camera = camera_response.json()
        camera_id = camera.get("id") or camera.get("_id")

        if not camera_id:
            raise AuthError("Invalid camera response")

        start_response = await client.post(
            f"{settings.CAMERA_SERVICE_URL}/capture/cameras/{camera_id}/start"
        )

        if start_response.status_code in (200, 201, 409):
            return

        raise AuthError("Failed to start capture")


async def _handle_agent_capture_on_logout(user_id: str, role: str | None):
    if role != "agent":
        return

    async with httpx.AsyncClient() as client:
        camera_response = await client.get(
            f"{settings.CAMERA_SERVICE_URL}/camera/cameras/assigned/user/{user_id}"
        )

        if camera_response.status_code == 404:
            return

        if camera_response.status_code != 200:
            raise AuthError("Failed to get assigned camera")

        camera = camera_response.json()
        camera_id = camera.get("id") or camera.get("_id")

        if not camera_id:
            raise AuthError("Invalid camera response")

        stop_response = await client.post(
            f"{settings.CAMERA_SERVICE_URL}/capture/cameras/{camera_id}/stop"
        )

        if stop_response.status_code in (200, 404):
            return

        raise AuthError("Failed to stop capture")


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

    try:
        await _handle_agent_capture_on_login(user)
    except AuthError:
        pass

    token = create_access_token(
        {"sub": str(user["_id"]), "role": user.get("role")},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": token, "token_type": "bearer"}

async def logout_user(token: str):
    payload = decode_token(token)

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id:
        raise AuthError("Invalid token")

    try:
        await _handle_agent_capture_on_logout(user_id, role)
    except AuthError:
        pass

    return {"message": "Logout successful"}


def verify_token(token: str):
    payload = decode_token(token)
    return {
        "valid": True,
        "user_id": payload.get("sub"),
        "role": payload.get("role"),
        "exp": payload.get("exp")
    }