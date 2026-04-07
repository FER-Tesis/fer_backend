from typing import List

from fastapi import APIRouter, HTTPException, status

from app.schemas.camera_alert_schema import (
    CameraAlertCreate,
    CameraAlertResponse,
)
from app.services import camera_alert_service

router = APIRouter()

@router.post(
    "",
    response_model=CameraAlertResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_camera_alert(payload: CameraAlertCreate):
    try:
        return await camera_alert_service.create_camera_alert(payload)

    except camera_alert_service.CameraAlertDomainError as e:
        if str(e) == "invalid_description":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Description is required",
            )

        if str(e) == "camera_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Camera not found",
            )

        if str(e) == "agent_not_assigned":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Camera has no assigned agent",
            )

        if str(e) == "active_alert_already_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active alert already exists for this camera",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid camera alert data",
        )


@router.get(
    "",
    response_model=List[CameraAlertResponse],
    status_code=status.HTTP_200_OK,
)
async def list_camera_alerts():
    return await camera_alert_service.list_camera_alerts()


@router.get(
    "/supervisor/{supervisor_id}/active",
    response_model=List[CameraAlertResponse],
    status_code=status.HTTP_200_OK,
)
async def list_active_camera_alerts_for_supervisor(supervisor_id: str):
    try:
        return await camera_alert_service.list_active_camera_alerts_for_supervisor(
            supervisor_id
        )

    except camera_alert_service.CameraAlertDomainError as e:
        if str(e) == "supervisor_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supervisor not found or user-service error",
            )

        if str(e) == "camera_service_error":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Camera service error",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request",
        )


@router.get(
    "/supervisor/{supervisor_id}/history",
    response_model=List[CameraAlertResponse],
    status_code=status.HTTP_200_OK,
)
async def list_camera_alert_history_for_supervisor(supervisor_id: str):
    try:
        return await camera_alert_service.list_camera_alert_history_for_supervisor(
            supervisor_id
        )

    except camera_alert_service.CameraAlertDomainError as e:
        if str(e) == "supervisor_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supervisor not found or user-service error",
            )

        if str(e) == "camera_service_error":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Camera service error",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request",
        )