from datetime import datetime, timezone
import httpx
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.events.event_bus import event_bus
from app.enums.alert_status import AlertStatus
from app.schemas.camera_alert_schema import CameraAlertCreate
from app.repositories import camera_alert_repository


class CameraAlertDomainError(ValueError):
    pass


async def _fetch_camera(camera_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = f"{settings.CAMERA_SERVICE_URL}/camera/cameras/{camera_id}"
        response = await client.get(url)

        if response.status_code != 200:
            raise CameraAlertDomainError("camera_not_found")

        return response.json()


async def _fetch_supervisor_agents(supervisor_id: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        url = f"{settings.USER_SERVICE_URL}/relations/supervisor/{supervisor_id}"
        response = await client.get(url)

        if response.status_code != 200:
            raise CameraAlertDomainError("supervisor_not_found")

        return response.json()


async def _get_assigned_agent_id_from_camera(camera: dict) -> str | None:
    return camera.get("assigned_user_id") or camera.get("assigned_agent_id")


async def get_supervisor_agent_ids(supervisor_id: str) -> list[str]:
    agents = await _fetch_supervisor_agents(supervisor_id)
    return [str(agent["id"]) for agent in agents]


async def create_camera_alert(payload: CameraAlertCreate) -> dict:
    description = payload.description.strip()

    if not description:
        raise CameraAlertDomainError("invalid_description")

    camera = await _fetch_camera(payload.camera_id)
    agent_id = await _get_assigned_agent_id_from_camera(camera)

    if not agent_id:
        raise CameraAlertDomainError("agent_not_assigned")

    existing_active = await camera_alert_repository.get_active_alert_by_camera_id(
        payload.camera_id
    )

    if existing_active:
        await camera_alert_repository.resolve_camera_alert(existing_active["_id"])

        await event_bus.publish(
            "camera-alert-resolved",
            {
                "alert_id": existing_active["_id"],
                "agent_id": existing_active["agent_id"],
            },
        )

    alert_data = {
        "camera_id": payload.camera_id,
        "agent_id": agent_id,
        "description": description,
        "status": AlertStatus.active.value,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        created = await camera_alert_repository.create_camera_alert(alert_data)

        await event_bus.publish(
            "camera-alert-created",
            {
                "_id": created["_id"],
                "camera_id": created["camera_id"],
                "agent_id": created["agent_id"],
                "description": created["description"],
                "status": created["status"],
                "created_at": created["created_at"].isoformat(),
            },
        )

        return created

    except DuplicateKeyError:
        raise CameraAlertDomainError("active_alert_already_exists")


async def recreate_active_alert_for_camera_assignment_change(camera_id: str):
    existing_active = await camera_alert_repository.get_active_alert_by_camera_id(camera_id)

    if not existing_active:
        return None

    camera = await _fetch_camera(camera_id)
    new_agent_id = await _get_assigned_agent_id_from_camera(camera)

    await camera_alert_repository.resolve_camera_alert(existing_active["_id"])

    await event_bus.publish(
        "camera-alert-resolved",
        {
            "alert_id": existing_active["_id"],
            "agent_id": existing_active["agent_id"],
        },
    )

    if not new_agent_id:
        return None

    if str(existing_active["agent_id"]) == str(new_agent_id):
        return None

    alert_data = {
        "camera_id": camera_id,
        "agent_id": new_agent_id,
        "description": existing_active["description"],
        "status": AlertStatus.active.value,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        created = await camera_alert_repository.create_camera_alert(alert_data)

        await event_bus.publish(
            "camera-alert-created",
            {
                "_id": created["_id"],
                "camera_id": created["camera_id"],
                "agent_id": created["agent_id"],
                "description": created["description"],
                "status": created["status"],
                "created_at": created["created_at"].isoformat(),
            },
        )

        return created

    except DuplicateKeyError:
        raise CameraAlertDomainError("active_alert_already_exists")


async def resolve_camera_alert(alert_id: str):
    alert = await camera_alert_repository.get_camera_alert_by_id(alert_id)

    if not alert:
        raise CameraAlertDomainError("camera_alert_not_found")

    await camera_alert_repository.resolve_camera_alert(alert_id)

    await event_bus.publish(
        "camera-alert-resolved",
        {
            "alert_id": alert["_id"],
            "agent_id": alert["agent_id"],
        },
    )


async def delete_camera_alert(alert_id: str):
    alert = await camera_alert_repository.get_camera_alert_by_id(alert_id)

    if not alert:
        raise CameraAlertDomainError("camera_alert_not_found")

    await camera_alert_repository.delete_camera_alert(alert_id)

    await event_bus.publish(
        "camera-alert-deleted",
        {
            "alert_id": alert["_id"],
            "agent_id": alert["agent_id"],
        },
    )


async def list_camera_alerts(limit: int = 100):
    return await camera_alert_repository.get_camera_alerts(limit)


async def list_active_camera_alerts_for_agent(
    agent_id: str,
    limit: int = 100,
):
    return await camera_alert_repository.get_active_camera_alerts_for_agent(
        agent_id=agent_id,
        limit=limit,
    )


async def list_active_camera_alerts_for_supervisor(
    supervisor_id: str,
    limit: int = 100,
):
    agent_ids = await get_supervisor_agent_ids(supervisor_id)

    return await camera_alert_repository.get_active_camera_alerts_for_agents(
        agent_ids=agent_ids,
        limit=limit,
    )


async def list_camera_alert_history_for_supervisor(
    supervisor_id: str,
    limit: int = 100,
):
    agent_ids = await get_supervisor_agent_ids(supervisor_id)

    return await camera_alert_repository.get_camera_alert_history_for_agents(
        agent_ids=agent_ids,
        limit=limit,
    )