from fastapi import APIRouter, HTTPException, status
from typing import List
from app.schemas.camera_schema import CameraCreate, CameraUpdate, CameraResponse, UpdateCameraStatusRequest
from app.services import camera_service

router = APIRouter()

@router.post("/cameras", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(camera: CameraCreate):
    try:
        new_camera = await camera_service.create_camera(camera)

        return new_camera
    except camera_service.CameraDomainError as e:
        if str(e) == "duplicate_ip":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A camera with this IP already exists")
        
        if str(e) == "invalid_status":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
        
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid camera data")

@router.get("/cameras", response_model=List[CameraResponse])
async def list_cameras():
    return await camera_service.list_cameras()

@router.get("/cameras/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: str):
    camera = await camera_service.get_camera(camera_id)

    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    
    return camera

@router.patch("/cameras/{camera_id}", response_model=CameraResponse)
async def update_camera(camera_id: str, camera_update: CameraUpdate):
    try:
        updated = await camera_service.update_camera(
            camera_id, camera_update.model_dump(exclude_unset=True)
        )

        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
        
        return updated

    except camera_service.CameraDomainError as e:
        if str(e) == "invalid_status":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status"
            )

        if str(e) == "cannot_activate_from_maintenance":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot activate camera directly from maintenance"
            )

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid camera update")

@router.delete("/cameras/{camera_id}")
async def delete_camera(camera_id: str):
    deleted = await camera_service.delete_camera(camera_id)
    
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    
    return {"message": "Camera deleted successfully"}

@router.get("/cameras/assigned/user/{user_id}", response_model=CameraResponse)
async def get_camera_by_assigned_user(user_id: str):
    camera = await camera_service.get_camera_by_assigned_user(user_id)

    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No camera assigned to this user"
        )

    return camera

@router.patch("/cameras/{camera_id}/status", response_model=CameraResponse)
async def update_camera_status(camera_id: str, payload: UpdateCameraStatusRequest):
    try:
        return await camera_service.update_camera_status(
            camera_id=camera_id,
            status=payload.status
        )

    except camera_service.CameraDomainError as e:
        if str(e) == "camera_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found"
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid camera status update request"
        )