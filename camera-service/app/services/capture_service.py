from datetime import datetime
from uuid import uuid4
import httpx

from app.core.config import settings
from app.repositories import camera_repository, capture_repository


class CaptureDomainError(ValueError):
    """Errores de negocio en el servicio de captura."""
    pass


def _validate_camera_available_for_monitoring(camera: dict) -> None:
    status = camera.get("status")

    if status == "inactive":
        raise CaptureDomainError("camera_inactive")

    if status == "maintenance":
        raise CaptureDomainError("camera_in_maintenance")


async def get_hub_camera_status(camera_id: str, active_session: dict | None = None) -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.CAMERA_HUB_URL}/{camera_id}/status"
            )

        if response.status_code >= 400:
            hub_active = False
        else:
            data = response.json()
            hub_active = bool(data.get("active", False))

    except httpx.HTTPError:
        hub_active = False

    if active_session and not hub_active:
        await capture_repository.close_capture_session(active_session["_id"])
        return False

    return hub_active


async def sync_camera_monitoring_status(camera: dict) -> bool:
    camera_id = camera["_id"]

    active_session = await capture_repository.get_active_session_by_camera_id(camera_id)

    if camera.get("status") != "active":
        if active_session:
            await capture_repository.close_capture_session(active_session["_id"])
        return False

    if not active_session:
        return False

    hub_active = await get_hub_camera_status(camera_id, active_session)

    if active_session and hub_active:
        return True

    return False


async def start_capture(camera_id: str) -> dict:
    camera = await camera_repository.get_camera_by_id(camera_id)
    if not camera:
        raise CaptureDomainError("camera_not_found")

    _validate_camera_available_for_monitoring(camera)

    is_really_active = await sync_camera_monitoring_status(camera)
    if is_really_active:
        raise CaptureDomainError("capture_already_active")

    capture_session_id = str(uuid4())

    session_data = {
        "_id": capture_session_id,
        "camera_id": camera_id,
        "active": True,
        "started_at": datetime.utcnow(),
        "ended_at": None
    }

    await capture_repository.create_capture_session(session_data)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.CAMERA_HUB_URL}/{camera_id}/start",
                json={"capture_session_id": capture_session_id}
            )

        if response.status_code >= 400:
            await capture_repository.close_capture_session(capture_session_id)
            raise CaptureDomainError("hub_start_failed")

    except httpx.HTTPError:
        await capture_repository.close_capture_session(capture_session_id)
        raise CaptureDomainError("hub_unreachable")

    return {
        "capture_session_id": capture_session_id,
        "camera_id": camera_id,
        "active": True
    }


async def stop_capture(camera_id: str) -> dict:
    camera = await camera_repository.get_camera_by_id(camera_id)
    if not camera:
        raise CaptureDomainError("camera_not_found")

    active_session = await capture_repository.get_active_session_by_camera_id(camera_id)
    if not active_session:
        raise CaptureDomainError("active_session_not_found")

    session_id = active_session["_id"]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.CAMERA_HUB_URL}/{camera_id}/stop"
            )

        if response.status_code >= 400:
            raise CaptureDomainError("hub_stop_failed")

    except httpx.HTTPError:
        raise CaptureDomainError("hub_unreachable")

    closed_session = await capture_repository.close_capture_session(session_id)

    return {
        "message": "Capture stopped successfully",
        "capture_session_id": session_id,
        "camera_id": camera_id,
        "active": closed_session["active"]
    }


async def get_capture_session_active(capture_session_id: str) -> dict:
    session = await capture_repository.get_session_by_id(capture_session_id)

    if not session:
        raise CaptureDomainError("capture_session_not_found")

    return {
        "capture_session_id": capture_session_id,
        "active": session["active"]
    }


async def get_camera_monitoring_status(camera_id: str) -> dict:
    camera = await camera_repository.get_camera_by_id(camera_id)
    if not camera:
        raise CaptureDomainError("camera_not_found")

    active = await sync_camera_monitoring_status(camera)

    return {
        "camera_id": camera_id,
        "active": active
    }