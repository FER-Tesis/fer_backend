from datetime import datetime
import httpx
from fastapi import HTTPException, status
from app.repositories import camera_repository
from app.schemas.camera_schema import CameraCreate, CameraUpdate
from app.enums.camera_status import CameraStatus
from app.core.config import settings

class CameraDomainError(ValueError):
    """Errores de negocio en el servicio de cámaras."""
    pass

async def _create_camera_alert(camera_id: str):
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{settings.ALERT_SERVICE_URL}",
            json={
                "camera_id": camera_id,
                "description": "La cámara fue reportada en mantenimiento."
            }
        )

        if response.status_code not in (200, 201):
            raise CameraDomainError("camera_alert_creation_failed")

async def validate_assigned_user(user_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.USER_SERVICE_URL}/users/{user_id}")

        if response.status_code != 200:
            raise CameraDomainError("user_not_found")

        user = response.json()

        if user.get("role") != "agent":
            raise CameraDomainError("user_not_agent")


async def create_camera(camera: CameraCreate) -> dict:
    if camera.assigned_user_id:
        await validate_assigned_user(camera.assigned_user_id)

    existing = await camera_repository.get_camera_by_ip(camera.ip_address)
    if existing:
        raise CameraDomainError("duplicate_ip")

    try:
        validated_status = CameraStatus(camera.status)
    except ValueError:
        raise CameraDomainError("invalid_status")

    data = camera.model_dump()
    data["status"] = validated_status.value

    return await camera_repository.create_camera(data)

async def list_cameras() -> list[dict]:
    return await camera_repository.get_all_cameras()

async def get_camera(camera_id: str) -> dict | None:
    return await camera_repository.get_camera_by_id(camera_id)

async def update_camera(camera_id: str, update: dict) -> dict | None:
    if "assigned_user_id" in update and update["assigned_user_id"]:
        await validate_assigned_user(update["assigned_user_id"])

    if "status" in update and update["status"] is not None:
        try:
            validated_status = CameraStatus(update["status"])
            update["status"] = validated_status.value
        except ValueError:
            raise CameraDomainError("invalid_status")

    if update.get("status") == CameraStatus.active.value:
        current = await camera_repository.get_camera_by_id(camera_id)

        if current and current.get("status") == CameraStatus.maintenance.value:
            raise CameraDomainError("cannot_activate_from_maintenance")

    return await camera_repository.update_camera(camera_id, update)

async def delete_camera(camera_id: str) -> bool:
    return await camera_repository.delete_camera(camera_id)

async def get_camera_by_assigned_user(user_id: str) -> dict | None:
    return await camera_repository.get_camera_by_assigned_user_id(user_id)

async def update_camera_status(camera_id: str, status: CameraStatus) -> dict:
    camera = await camera_repository.get_camera_by_id(camera_id)
    if not camera:
        raise CameraDomainError("camera_not_found")

    previous_status = camera["status"]

    updated_camera = await camera_repository.update_camera_status(
        camera_id=camera_id,
        status=status.value
    )

    if (
        status == CameraStatus.maintenance
        and previous_status != CameraStatus.maintenance.value
    ):
        try:
            await _create_camera_alert(camera_id)
        except CameraDomainError:
            raise

    return updated_camera