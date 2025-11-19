from datetime import datetime
import httpx

from app.core.config import settings
from app.enums.emotion_type import Emotion
from app.schemas.emotion_schema import EmotionEventCreate
from app.repositories import emotion_event_repository, current_status_repository
from app.utils.date_helpers import ensure_utc, is_newer


class EmotionDomainError(ValueError):
    """Errores de negocio en el servicio de monitoreo emocional."""
    pass


async def _fetch_camera(camera_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = f"{settings.CAMERA_SERVICE_URL}/cameras/{camera_id}"
        response = await client.get(url)

        if response.status_code != 200:
            raise EmotionDomainError("camera_not_found")

        return response.json()


async def _validate_agent_from_camera(camera: dict) -> str:
    agent_id = camera.get("assigned_user_id")

    if not agent_id:
        raise EmotionDomainError("agent_not_assigned")

    return agent_id


async def register_emotion_event(event: EmotionEventCreate) -> dict:
    try:
        validated_emotion = Emotion(event.emotion)
    except ValueError:
        raise EmotionDomainError("invalid_emotion")

    normalized_timestamp = ensure_utc(event.timestamp)

    camera = await _fetch_camera(event.camera_id)

    agent_id = await _validate_agent_from_camera(camera)

    event_data = {
        "camera_id": event.camera_id,
        "agent_id": agent_id,
        "emotion": validated_emotion.value,
        "timestamp": normalized_timestamp,
    }

    created_event = await emotion_event_repository.create_emotion_event(event_data)

    current = await current_status_repository.get_status_by_camera_id(event.camera_id)

    if not current or is_newer(current["timestamp"], normalized_timestamp):
        await current_status_repository.upsert_status(
            camera_id=event.camera_id,
            agent_id=agent_id,
            emotion=validated_emotion.value,
            timestamp=normalized_timestamp,
        )

    return created_event


async def list_emotion_events(limit: int = 100):
    return await emotion_event_repository.get_emotion_events(limit)


async def list_current_statuses(limit: int = 100):
    return await current_status_repository.get_all_statuses(limit)


async def get_current_status(camera_id: str):
    return await current_status_repository.get_status_by_camera_id(camera_id)
