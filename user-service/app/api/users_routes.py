from fastapi import APIRouter, HTTPException, status
from app.schemas.user_schema import UserCreate, UserUpdate, UserResponse, UserLookup
from app.services import user_service
from typing import List

router = APIRouter()

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    new_user = await user_service.create_user(user)
    return new_user

@router.get("/users", response_model=List[UserResponse])
async def list_users():
    return await user_service.list_users()

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_update: UserUpdate):
    updated_user = await user_service.update_user(
        user_id, user_update.model_dump(exclude_unset=True)
        )
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@router.delete("/users/{user_id}")
async def delete_user(user_id: str):
    deleted = await user_service.delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@router.post("/find", status_code=status.HTTP_200_OK)
async def find_user(data: UserLookup):
    user = await user_service.get_user_by_email(data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user