from fastapi import APIRouter, HTTPException, status
from typing import List

from app.schemas.supervisor_agent_schema import (
    SupervisorAgentCreate,
    SupervisorAgentResponse,
    AgentMinimal
)
from app.services import supervisor_agent_service

router = APIRouter()


@router.post(
    "",
    response_model=SupervisorAgentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_relation(payload: SupervisorAgentCreate):
    try:
        return await supervisor_agent_service.create_relation(payload)

    except supervisor_agent_service.SupervisorAgentDomainError as e:
        code = str(e)

        if code == "supervisor_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supervisor not found",
            )

        if code == "agent_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        if code == "agent_already_assigned":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent already assigned",
            )

        if code == "cannot_assign_self":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A supervisor cannot be their own agent",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid relation data",
        )

@router.get(
    "/supervisor/{supervisor_id}",
    response_model=List[AgentMinimal],
    status_code=status.HTTP_200_OK,
)
async def list_agents(supervisor_id: str):
    return await supervisor_agent_service.list_by_supervisor(supervisor_id)


@router.delete(
    "/{relation_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_relation(relation_id: str):
    try:
        await supervisor_agent_service.delete_relation(relation_id)
        return {"message": "Relation deleted successfully"}

    except supervisor_agent_service.SupervisorAgentDomainError as e:
        if str(e) == "relation_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Relation not found",
            )
        
@router.get("/available-agents")
async def available_agents():
    return await supervisor_agent_service.get_available_agents()

@router.delete(
    "/{supervisor_id}/{agent_id}",
    status_code=status.HTTP_200_OK
)
async def remove_agent(supervisor_id: str, agent_id: str):
    deleted = await supervisor_agent_service.remove_agent(supervisor_id, agent_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Relación no encontrada")

    return {"message": "Agente removido correctamente"}