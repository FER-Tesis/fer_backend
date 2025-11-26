import httpx
from app.core.config import settings
from datetime import datetime, timedelta, timezone, date
from typing import List

from app.repositories import (
    emotion_event_repository,
    current_status_repository,
)

from app.schemas.monitoring_schema import (
    AgentCurrentEmotionResponse,
    AgentDayHistoryResponse,
    AgentWeekHistoryResponse,
    SupervisorAgentStatus
)

from app.enums.emotion_type import Emotion
from app.utils.date_helpers import ensure_utc


MAX_DAY_POINTS = 300

def _day_interval_utc(day: date):
    start = datetime(day.year, day.month, day.day, 13, 0, 0, tzinfo=timezone.utc)
    end = datetime(day.year, day.month, day.day, 23, 0, 0, tzinfo=timezone.utc)
    return start, end

def _hour_mode(emotions: list[str]) -> str | None:
    if not emotions:
        return None

    if all(e == "neutral" for e in emotions):
        return "neutral"

    filtered = [e for e in emotions if e != "neutral"]

    if not filtered:
        return "neutral"

    return max(set(filtered), key=filtered.count)

def _compute_hourly_modes(day: date, events: list):
    buckets = []

    normalized = [
        {
            "emotion": ev["emotion"],
            "ts": ensure_utc(ev["timestamp"])
        }
        for ev in events
    ]

    for hour_peru in range(7, 18):
        utc_start = datetime(day.year, day.month, day.day, hour_peru + 5, 0, 0, tzinfo=timezone.utc)
        utc_end   = datetime(day.year, day.month, day.day, hour_peru + 6, 0, 0, tzinfo=timezone.utc)

        emotions_in_bucket = [
            ev["emotion"]
            for ev in normalized
            if utc_start <= ev["ts"] < utc_end
        ]

        if not emotions_in_bucket:
            buckets.append(None)
            continue

        dominant = _hour_mode(emotions_in_bucket)

        buckets.append(Emotion(dominant) if dominant else None)

    return buckets

def peru_today():
    now_utc = datetime.now(timezone.utc)
    now_peru = now_utc - timedelta(hours=5)
    return now_peru.date()

async def get_agent_current(agent_id: str) -> AgentCurrentEmotionResponse:
    status = await current_status_repository.get_status_by_agent_id(agent_id)

    if not status:
        return AgentCurrentEmotionResponse(
            emotion=None,
            timestamp=None
        )

    return AgentCurrentEmotionResponse(
        emotion=status["emotion"],
        timestamp=status["timestamp"],
    )

async def get_agent_day_history(agent_id: str) -> AgentDayHistoryResponse:
    today = peru_today()
    start, end = _day_interval_utc(today)

    events = await emotion_event_repository.get_emotion_events_for_agent_between(
        agent_id, start, end
    )

    hourly_modes = _compute_hourly_modes(today, events)

    labels = [f"{(h+1):02d}:00" for h in range(7, 18)]
    values = hourly_modes

    return AgentDayHistoryResponse(labels=labels, values=values)


async def get_agent_week_history(agent_id: str) -> AgentWeekHistoryResponse:
    today = peru_today()

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=5)

    query_start = datetime(week_start.year, week_start.month, week_start.day, 13, 0, 0, tzinfo=timezone.utc)
    query_end   = datetime(week_end.year, week_end.month, week_end.day, 23, 0, 0, tzinfo=timezone.utc)

    events = await emotion_event_repository.get_emotion_events_for_agent_between(
        agent_id,
        query_start,
        query_end,
    )

    events_by_day = {}
    for ev in events:
        day = ensure_utc(ev["timestamp"]).date()
        events_by_day.setdefault(day, []).append(ev["emotion"])

    labels = []
    values = []

    for i in range(6):
        day = week_start + timedelta(days=i)
        labels.append(day.isoformat())

        if day not in events_by_day:
            values.append(None)
            continue

        emotions = events_by_day[day]
        dominant = max(set(emotions), key=emotions.count)
        values.append(Emotion(dominant))

    return AgentWeekHistoryResponse(labels=labels, values=values)

async def get_supervisor_agents_with_status(supervisor_id: str):
    user_service_url = f"{settings.USER_SERVICE_URL}/relations/supervisor/{supervisor_id}"

    async with httpx.AsyncClient() as client:
        response = await client.get(user_service_url)

    if response.status_code != 200:
        raise ValueError("Supervisor not found or user-service error")

    agents = response.json()

    result = []

    for agent in agents:
        current = await get_agent_current(agent_id=agent["id"])

        result.append(
            SupervisorAgentStatus(
                id = agent["id"],
                name = agent["name"],
                email = agent["email"],
                emotion = current.emotion,
                timestamp = current.timestamp
            )
        )

    return result
