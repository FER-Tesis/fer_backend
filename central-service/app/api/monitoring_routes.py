from fastapi import APIRouter, HTTPException, status
from datetime import date
from typing import List

from app.schemas.monitoring_schema import (
    AgentCurrentEmotionResponse,
    AgentDayHistoryResponse,
    AgentWeekHistoryResponse,
    SupervisorAgentStatus
)

from app.services import monitoring_service

router = APIRouter()

@router.get("/agent/{agent_id}/current", response_model=AgentCurrentEmotionResponse)
async def get_current(agent_id: str):
    return await monitoring_service.get_agent_current(agent_id)


@router.get("/agent/{agent_id}/history/day", response_model=AgentDayHistoryResponse)
async def get_day(agent_id: str):
    return await monitoring_service.get_agent_day_history(agent_id)


@router.get("/agent/{agent_id}/history/week", response_model=AgentWeekHistoryResponse)
async def get_week(agent_id: str):
    return await monitoring_service.get_agent_week_history(agent_id)

@router.get("/supervisor/{supervisor_id}/agents", response_model=List[SupervisorAgentStatus])
async def get_supervisor_agents(supervisor_id: str):
    try:
        return await monitoring_service.get_supervisor_agents_with_status(supervisor_id)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")