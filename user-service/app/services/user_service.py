from app.repositories import user_repository
from app.schemas.user_schema import UserCreate
from app.core.security import hash_password

async def create_user(user_data: UserCreate):
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
