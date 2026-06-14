from app.repositories import user_repository
from app.schemas.user_schema import UserCreate, UsersMetrics
from app.core.security import hash_password

class UserDomainError(ValueError):
    """Errores de negocio en el servicio de usuarios."""
    pass

async def create_user(user_data: UserCreate):

    if await user_repository.exists_by_email(user_data.email):
        raise UserDomainError("Ya existe un usuario con este correo electrónico.")

    user_dict = user_data.model_dump()
    user_dict["password"] = hash_password(user_dict["password"])
    return await user_repository.create_user(user_dict)

async def list_users():
    return await user_repository.get_all_users()

async def get_user(user_id: str):
    return await user_repository.get_user_by_id(user_id)

async def update_user(user_id: str, data: dict):
    if "password" in data:
        data["password"] = hash_password(data["password"])
        
    return await user_repository.update_user(user_id, data)

async def delete_user(user_id: str):
    return await user_repository.delete_user(user_id)

async def get_user_by_email(email: str):
    return await user_repository.get_user_by_email(email)

async def get_users_metrics():
    total = await user_repository.count_all_users()
    active_agents = await user_repository.count_active_agents()

    return UsersMetrics(
        totalUsers=total,
        activeAgents=active_agents
    )
