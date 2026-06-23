import httpx

from app.core.config import settings
from app.events.alert_event_bus import alert_event_bus
from app.enums.emotion_alert_enum import EmotionAlertStatus
from app.repositories import emotion_alert_repository


class EmotionAlertDomainError(ValueError):
    pass


async def _fetch_supervisor_agents(supervisor_id: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        url = f"{settings.USER_SERVICE_URL}/relations/supervisor/{supervisor_id}"
        response = await client.get(url, timeout=5.0)

        if response.status_code != 200:
            raise EmotionAlertDomainError("supervisor_not_found")

        return response.json()


async def get_supervisor_agents(supervisor_id: str) -> list[dict]:
    agents = await _fetch_supervisor_agents(supervisor_id)

    return [
        {
            "id": str(agent["id"]),
            "name": agent.get("name", ""),
            "email": agent.get("email", ""),
        }
        for agent in agents
    ]


async def get_supervisor_agent_ids(supervisor_id: str) -> list[str]:
    agents = await get_supervisor_agents(supervisor_id)
    return [str(agent["id"]) for agent in agents]


async def list_pending_emotion_alerts_for_agent(
    agent_id: str,
    limit: int = 100,
):
    return await emotion_alert_repository.get_pending_alerts_by_agent(
        agent_id=agent_id,
        limit=limit,
    )


async def list_pending_emotion_alerts_for_supervisor(
    supervisor_id: str,
    limit: int = 100,
):
    agent_ids = await get_supervisor_agent_ids(supervisor_id)

    if not agent_ids:
        return []

    return await emotion_alert_repository.get_pending_alerts_by_agents(
        agent_ids=agent_ids,
        limit=limit,
    )


async def acknowledge_emotion_alert(alert_id: str):
    alert = await emotion_alert_repository.get_alert_by_id(alert_id)

    if not alert:
        raise EmotionAlertDomainError("emotion_alert_not_found")

    if alert["status"] != EmotionAlertStatus.pending.value:
        return alert

    updated = await emotion_alert_repository.update_alert(
        alert_id,
        {"status": EmotionAlertStatus.acknowledged.value},
    )

    await alert_event_bus.publish(
        "emotion-alert-acknowledged",
        {
            "alert_id": updated["_id"],
            "agent_id": updated["agent_id"],
            "supervisor_id": updated["supervisor_id"],
            "status": updated["status"],
        },
    )

    return updated

async def delete_emotion_alert_by_agent_id(agent_id: str):
    await emotion_alert_repository.delete_alerts_by_agent_id(agent_id)