from datetime import datetime
import httpx
import asyncio

from app.core.config import settings
from app.events.event_bus import event_bus
from app.events.alert_event_publisher import alert_event_publisher
from app.enums.emotion_type import Emotion
from app.schemas.emotion_schema import EmotionEventCreate
from app.repositories import emotion_event_repository, current_status_repository
from app.utils.date_helpers import ensure_utc, is_newer


class EmotionDomainError(ValueError):
    """Errores de negocio en el servicio de monitoreo emocional."""
    pass


async def _fetch_camera(camera_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        url = f"{settings.CAMERA_SERVICE_URL}/camera/cameras/{camera_id}"
        response = await client.get(url)

        if response.status_code != 200:
            raise EmotionDomainError("camera_not_found")

        return response.json()


async def _validate_agent_from_camera(camera: dict) -> str:
    agent_id = camera.get("assigned_user_id")

    if not agent_id:
        raise EmotionDomainError("agent_not_assigned")

    return agent_id

async def _validate_capture_session_active(capture_session_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.CAMERA_SERVICE_URL}/capture/sessions/{capture_session_id}/active"
        )

        if response.status_code == 404:
            raise EmotionDomainError("capture_session_not_found")

        if response.status_code != 200:
            raise EmotionDomainError("capture_session_validation_failed")

        data = response.json()

        if not data.get("active", False):
            raise EmotionDomainError("capture_session_inactive")
        

CAMERA_AGENT_CACHE = {}
CAMERA_SESSION_CACHE = {}


def _get_cached_agent_id(camera_id: str, capture_session_id: str):
    return CAMERA_AGENT_CACHE.get((capture_session_id, camera_id))


def _set_cached_agent_id(camera_id: str, capture_session_id: str, agent_id: str):
    CAMERA_AGENT_CACHE[(capture_session_id, camera_id)] = agent_id
    CAMERA_SESSION_CACHE[camera_id] = capture_session_id


def _clear_camera_agent_cache(camera_id: str):
    keys_to_delete = [
        key for key in CAMERA_AGENT_CACHE
        if key[1] == camera_id
    ]

    for key in keys_to_delete:
        del CAMERA_AGENT_CACHE[key]

async def register_emotion_event(event: EmotionEventCreate) -> dict:
    try:
        validated_emotion = Emotion(event.emotion)
    except ValueError:
        raise EmotionDomainError("invalid_emotion")

    normalized_timestamp = ensure_utc(event.timestamp)

    await _validate_capture_session_active(event.capture_session_id)

    last_session_id = CAMERA_SESSION_CACHE.get(event.camera_id)

    if last_session_id and last_session_id != event.capture_session_id:
        _clear_camera_agent_cache(event.camera_id)

    cached_agent_id = _get_cached_agent_id(
        event.camera_id,
        event.capture_session_id,
    )

    if cached_agent_id:
        agent_id = cached_agent_id
    else:
        camera = await _fetch_camera(event.camera_id)

        agent_id = await _validate_agent_from_camera(camera)

        _set_cached_agent_id(
            event.camera_id,
            event.capture_session_id,
            agent_id,
        )

    event_data = {
        "camera_id": event.camera_id,
        "capture_session_id": event.capture_session_id,
        "agent_id": agent_id,
        "emotion": validated_emotion.value,
        "timestamp": normalized_timestamp,
    }

    created_event = await emotion_event_repository.create_emotion_event(event_data)

    status_updated = await current_status_repository.upsert_status_if_newer(
        camera_id=event.camera_id,
        agent_id=agent_id,
        emotion=validated_emotion.value,
        timestamp=normalized_timestamp,
    )

    if status_updated:
        await asyncio.gather(
            event_bus.publish(
                "agent-emotion-updated",
                {
                    "agent_id": agent_id,
                    "emotion": validated_emotion.value,
                    "timestamp": normalized_timestamp.isoformat(),
                },
            ),
            alert_event_publisher.publish_emotion_alert_event(
                agent_id=agent_id,
                emotion=validated_emotion.value,
                timestamp=normalized_timestamp.isoformat(),
            ),
        )
    else:
        await alert_event_publisher.publish_emotion_alert_event(
            agent_id=agent_id,
            emotion=validated_emotion.value,
            timestamp=normalized_timestamp.isoformat(),
        )

    return created_event

async def list_emotion_events(limit: int = 100):
    return await emotion_event_repository.get_emotion_events(limit)


async def list_current_statuses(limit: int = 100):
    return await current_status_repository.get_all_statuses(limit)


async def get_current_status(camera_id: str):
    return await current_status_repository.get_status_by_camera_id(camera_id)
