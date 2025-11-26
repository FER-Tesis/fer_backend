from app.repositories import supervisor_agent_repository, user_repository
from app.schemas.supervisor_agent_schema import SupervisorAgentCreate


class SupervisorAgentDomainError(ValueError):
    """Errores de negocio en el servicio de relaciones supervisor-agente."""
    pass


async def create_relation(payload: SupervisorAgentCreate):
    supervisor_id = str(payload.supervisor_id)
    agent_id = str(payload.agent_id)

    supervisor = await user_repository.get_user_by_id(supervisor_id)
    if not supervisor:
        raise SupervisorAgentDomainError("supervisor_not_found")

    agent = await user_repository.get_user_by_id(agent_id)
    if not agent:
        raise SupervisorAgentDomainError("agent_not_found")

    if supervisor_id == agent_id:
        raise SupervisorAgentDomainError("cannot_assign_self")

    data = {
        "supervisor_id": supervisor_id,
        "agent_id": agent_id
    }

    return await supervisor_agent_repository.create_relation(data)


async def list_by_supervisor(supervisor_id: str):
    relations = await supervisor_agent_repository.get_by_supervisor(supervisor_id)
    agent_ids = [r["agent_id"] for r in relations]

    agents = []
    for agent_id in agent_ids:
        user = await user_repository.get_user_by_id(agent_id)
        if user:
            agents.append({
                "id": user["_id"],
                "name": user["name"],
                "email": user["email"]
            })

    return agents

async def delete_relation(relation_id: str):
    deleted = await supervisor_agent_repository.delete_relation(relation_id)
    if not deleted:
        raise SupervisorAgentDomainError("relation_not_found")

    return True

async def get_available_agents():
    agents = await user_repository.get_users_by_role("agent")

    relations = await supervisor_agent_repository.get_all_relations()
    assigned_ids = {r["agent_id"] for r in relations}

    free_agents = [
        {
            "id": str(a["_id"]),
            "name": a["name"]
        }
        for a in agents
        if str(a["_id"]) not in assigned_ids
    ]

    return free_agents

async def remove_agent(supervisor_id: str, agent_id: str) -> bool:
    return await supervisor_agent_repository.remove_by_supervisor_agent(supervisor_id, agent_id)
